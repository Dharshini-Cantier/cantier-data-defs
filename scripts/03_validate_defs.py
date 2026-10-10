"""CHECK 3 - CONSISTENCY: all definition files must agree with EACH OTHER (00 checks each file alone).
Errors fail the pull request. Warnings list things that are referenced but not written yet (planned work).
"""
import re
from collections import Counter

from defs import ROOT, Report, files, load_yaml, rel

rep = Report("03 cross-file check")

# ------------------------------------------------------------------ load
glossary, term_file = {}, {}
for p in files("glossary/*.yaml"):
    for k, v in load_yaml(p)["terms"].items():
        rep.check(k not in glossary, f"glossary: term '{k}' is in both {term_file.get(k)} and {rel(p)}")
        rep.check(v["glossary_term_id"].split("/")[-1] == k, f"{rel(p)}: term '{k}' has glossary_term_id {v['glossary_term_id']}")
        glossary[k], term_file[k] = v, rel(p)
measures = {k for k, f in term_file.items() if f.endswith("measurement_types.yaml")}

onto = load_yaml(ROOT / "ontology" / "manufacturing.yaml")
classes = set(onto["classes"])
catalogue = load_yaml(ROOT / "tables" / "catalogue.yaml")["tables"]
tables = {}
for p in files("tables/*/*.yaml"):
    if p.name == "catalogue.yaml":
        continue
    t = load_yaml(p)
    rep.check(t["name"] == f"{p.parent.name}.{p.stem}", f"{rel(p)}: name '{t['name']}' must equal folder.file '{p.parent.name}.{p.stem}'")
    rep.check(t["layer"] == p.parent.name, f"{rel(p)}: layer '{t['layer']}' must equal the folder")
    tables[t["name"]] = t
known_tables = set(tables) | set(catalogue)
templates = {load_yaml(p)["template"]: load_yaml(p) for p in files("mappings/iiot/templates/*.yaml")}
assets = [a for p in files("assets/*.yaml") for a in load_yaml(p)["assets"]]
contracts = {load_yaml(p)["id"]: (p, load_yaml(p)) for p in files("contracts/*.yaml")}
kpis = [(p, k) for p in files("kpi/*.yaml") for k in load_yaml(p)["kpis"]]
sources = load_yaml(ROOT / "sources.yaml")
bronze_names = {t["name"] for s in sources.values() for t in s.get("tables", [])}

# ------------------------------------------------------------------ 1. glossary points at real things
for k, t in glossary.items():
    for c in filter(None, [t.get("observes"), t.get("ontology_class")]):
        rep.check(c in classes, f"glossary '{k}': ontology class '{c}' does not exist")
    for tb in t.get("evidence_for", []) + t.get("silver_tables", []):
        rep.warn(tb in known_tables, f"glossary '{k}': table {tb} is not in tables/catalogue.yaml")
    rng = t.get("valid_range")
    if rng and "min" in rng and "max" in rng:
        rep.check(rng["min"] <= rng["max"], f"glossary '{k}': valid_range min > max")
    if t.get("pattern"):
        try:
            re.compile(t["pattern"])
        except re.error:
            rep.check(False, f"glossary '{k}': broken pattern")

# ------------------------------------------------------------------ 2. tables: every column has a term (same type) or is technical
for name, t in tables.items():
    cols = {c["name"]: c for c in t["columns"]}
    rep.check(len(cols) == len(t["columns"]), f"{name}: duplicate column names")
    rep.check(name in catalogue and catalogue[name]["has_spec"], f"{name}: must be in tables/catalogue.yaml with has_spec: true")
    for c in t["columns"]:
        if c.get("technical"):
            continue
        g = glossary.get(c.get("term"))
        if rep.check(g is not None, f"{name}.{c['name']}: glossary term '{c.get('term')}' not found (add it, or mark technical: true)"):
            rep.check(g["data_type"] == c["type"] or {g["data_type"], c["type"]} <= {"int", "bigint"},
                      f"{name}.{c['name']}: type {c['type']} but glossary '{c['term']}' says {g['data_type']}")
    for k in t["primary_key"]:
        rep.check(k in cols, f"{name}: primary key '{k}' is not a column")
        rep.check(not cols.get(k, {}).get("nullable", False), f"{name}: primary key '{k}' must be nullable: false")
    for part in t.get("partition_by", []):
        m = re.match(r"\w+\((\w+)\)$", part) or re.match(r"(\w+)$", part)
        rep.check(bool(m) and m.group(1) in cols, f"{name}: partition '{part}' uses an unknown column")
for name, c in catalogue.items():
    rep.check(not c["has_spec"] or name in tables, f"tables/catalogue.yaml: {name} has_spec: true but tables/{name.replace('.', '/')}.yaml is missing")

# ------------------------------------------------------------------ 3. IIoT templates use real measurement types, with the same type + unit
by_machine = {a["machine_id"]: a for a in assets}
for name, tp in templates.items():
    tags = [x["tag_name"] for x in tp["tags"]]
    rep.check(len(tags) == len(set(tags)), f"template {name}: duplicate tag names")
    for m in tp["machines"]:
        a = by_machine.get(m)
        if rep.check(a is not None, f"template {name}: machine {m} is not in assets/"):
            rep.check(a["template"] == name, f"template {name}: machine {m} is registered with template {a['template']}")
    for x in tp["tags"]:
        g = glossary.get(x["measurement_type"])
        where = f"template {name}/{x['tag_name']}"
        if not rep.check(g is not None and x["measurement_type"] in measures, f"{where}: measurement type '{x['measurement_type']}' not in glossary/measurement_types.yaml"):
            continue
        rep.check(g["data_type"] == x["data_type"], f"{where}: data_type {x['data_type']} differs from glossary ({g['data_type']})")
        rep.check(g.get("unit") == x.get("unit"), f"{where}: unit '{x.get('unit')}' differs from glossary '{g.get('unit')}'")
        for tb in filter(None, [x.get("bronze_table"), x.get("silver_table")]):
            rep.warn(tb in known_tables, f"{where}: table {tb} is not in tables/catalogue.yaml")
for a in assets:
    rep.check(a["template"] in templates, f"asset {a['machine_id']}: template {a['template']} has no file in mappings/iiot/templates/")

# ------------------------------------------------------------------ 4. contracts
for cid, (p, c) in contracts.items():
    rep.check(p.stem == cid, f"{rel(p)}: file name must equal contract id '{cid}'")
    if c.get("extends"):
        rep.check(c["extends"] in contracts, f"{cid}: extends unknown contract '{c['extends']}'")
    names = [f["name"] for f in c["fields"]]
    rep.check(len(names) == len(set(names)), f"{cid}: duplicate field names")
    if c.get("extends") in contracts:
        parent = {x["name"] for x in contracts[c["extends"]][1]["fields"]}
        rep.check(not parent & set(names), f"{cid}: fields {sorted(parent & set(names))} are already in {c['extends']}")
    for f in c["fields"]:
        if f.get("term"):
            rep.check(f["term"] in glossary, f"{cid}.{f['name']}: glossary term '{f['term']}' not found")
    for k in c.get("key", []):
        all_fields = names + ([x["name"] for x in contracts[c["extends"]][1]["fields"]] if c.get("extends") in contracts else [])
        rep.check(k in all_fields, f"{cid}: key field '{k}' is not a field")
    for tb in filter(None, [c.get("bronze_table"), c.get("silver_table")]):
        rep.warn(tb in known_tables, f"{cid}: table {tb} is not in tables/catalogue.yaml")
    labels = {g.get("label") for g in glossary.values()}
    for tag in c.get("allowed_tags", []):
        rep.check(tag in labels, f"{cid}: allowed tag '{tag}' is not a glossary measurement")

# ------------------------------------------------------------------ 5. DQ rules use real columns
EXPR_WORDS = {"and", "or", "not", "True", "False", "None", "in", "is"}
for p in files("dq/*.yaml"):
    d = load_yaml(p)
    t = tables.get(d["table"])
    if not rep.check(t is not None, f"{rel(p)}: table {d['table']} has no spec"):
        continue
    cols = {c["name"]: c for c in t["columns"]}
    ids = [r["id"] for r in d["rules"]]
    rep.check(len(ids) == len(set(ids)), f"{rel(p)}: duplicate rule ids")
    for r in d["rules"]:
        used = r.get("columns", [r["column"]] if "column" in r else [])
        if r["type"] == "expression":
            used = [w for w in re.findall(r"[A-Za-z_]\w*", r["check"]) if w not in EXPR_WORDS]
        for c in used:
            rep.check(c in cols, f"{rel(p)} {r['id']}: column '{c}' does not exist in {d['table']}")
        if r["type"] == "pattern":
            try:
                re.compile(r["pattern"])
            except re.error as e:
                rep.check(False, f"{rel(p)} {r['id']}: broken pattern ({e})")
for name, t in tables.items():
    if t["layer"] in ("silver", "ops"):
        rep.check((ROOT / "dq" / f"{name.split('.', 1)[1]}.yaml").exists(), f"{name}: Silver/ops table has no dq/ file (B2.8)")

# ------------------------------------------------------------------ 6. KPIs
nums = [k["number"] for _, k in kpis]
rep.check(len(nums) == len(set(nums)), "kpi: duplicate KPI numbers")
rep.check(Counter(k["id"] for _, k in kpis).most_common(1)[0][1] == 1 if kpis else True, "kpi: duplicate KPI ids")
for p, k in kpis:
    for tb in k.get("sources", []) + ([k["gold_table"]] if k.get("gold_table") else []):
        rep.warn(tb in known_tables, f"kpi {k['id']}: table {tb} is not in tables/catalogue.yaml")

# ------------------------------------------------------------------ 7. MES catalogue + MES mappings
mes = load_yaml(ROOT / "mappings" / "mes_catalogue.yaml")["tables"]
for e in mes:
    if e.get("silver_target"):
        rep.warn(e["silver_target"] in known_tables, f"mes_catalogue {e['mes_tables'][0]}: {e['silver_target']} is not in tables/catalogue.yaml")
    for n in e.get("kpis", []):
        rep.check(n in nums, f"mes_catalogue {e['mes_tables'][0]}: KPI #{n} does not exist")
mapped = Counter()
SNAKE = re.compile(r"^_?[a-z][a-z0-9_]*$")
for name, t in tables.items():
    if t["layer"] != "bronze":
        for c in t["columns"]:
            rep.check(bool(SNAKE.match(c["name"])), f"{name}.{c['name']}: Silver/Gold/ops column names must be snake_case (docs/CANONICAL_STANDARDS.md)")
for p in files("mappings/mes/*.yaml") + files("mappings/iiot/streams/*.yaml"):
    m = load_yaml(p)
    where = rel(p)
    t = tables.get(m["target_table"])
    mapped[m["target_table"]] += 1
    if not rep.check(t is not None, f"{where}: target_table {m['target_table']} has no table spec"):
        continue
    cols = {c["name"]: c for c in t["columns"]}
    targets = [c["target"] for c in m["columns"]]
    for x in targets:
        rep.check(x in cols, f"{where}: target '{x}' is not a column of {t['name']}")
    for x in cols:
        rep.check(targets.count(x) == 1, f"{where}: column '{x}' mapped {targets.count(x)} times (need exactly 1)")
    aliases = m["source"]["tables"]
    bronze_cols = {}
    for a, b in aliases.items():
        rep.check(b in known_tables or b.split(".", 1)[1] in bronze_names, f"{where}: source {b} is not a known Bronze table")
        if b in tables:
            bronze_cols[a] = {c["name"] for c in tables[b]["columns"]}
    refs = [c["from"] for c in m["columns"] if "from" in c]
    refs += [i for c in m["columns"] for i in c.get("transform", {}).get("inputs", [])]
    refs += (m["cdc"]["key"] + [m["cdc"]["order_by"], m["cdc"]["op_column"]]) if m.get("cdc") else []
    refs += [c["from"] for c in (m.get("rejects") or {}).get("columns", []) if "from" in c]
    for f in refs:
        a, _, colname = f.partition(".")
        if rep.check(a in aliases, f"{where}: '{f}' uses an alias that is not in source.tables"):
            if a in bronze_cols:
                rep.check(colname in bronze_cols[a], f"{where}: '{f}' - column {colname} is not in the Bronze spec {aliases[a]}")
    tag_map = m.get("tag_map") or {}
    for src, tm in tag_map.items():
        rep.check(tm["measurement_type"] in measures, f"{where}: tag_map {src} -> '{tm['measurement_type']}' is not in glossary/measurement_types.yaml")
        if tm.get("source_unit"):
            rep.check("factor" in tm, f"{where}: tag_map {src} has source_unit but no factor")
    for c in m["columns"]:
        lk = c.get("lookup")
        if not lk:
            continue
        if lk["map"] == "code_map":
            g = glossary.get(lk["source_type"], {})
            rep.check(lk["source_system"] in g.get("source_codes", {}),
                      f"{where}: {c['target']} code_map needs glossary '{lk['source_type']}' source_codes.{lk['source_system']}")
            vals = set(g.get("source_codes", {}).get(lk["source_system"], {}).values())
            if g.get("enum_values"):
                rep.check(vals <= set(g["enum_values"]), f"{where}: code map of '{lk['source_type']}' gives values outside enum_values")
        if lk["map"] == "tag_map":
            rep.check(bool(tag_map), f"{where}: {c['target']} uses tag_map but the file has no tag_map")
            rep.check(lk.get("attribute", "measurement_type") in ("measurement_type", "unit"), f"{where}: tag_map attribute must be measurement_type or unit")
        if lk["map"] == "identity_map" and lk.get("attribute"):
            rep.check(lk["attribute"] in {"process", "line", "template", "name", "criticality", "mes_asset_id", "cmms_asset_id", "machine_id"},
                      f"{where}: identity_map attribute '{lk['attribute']}' is not an asset attribute")
    rj = m.get("rejects")
    if rj:
        rt = tables.get(rj["table"])
        if rep.check(rt is not None, f"{where}: rejects table {rj['table']} has no spec"):
            rcols = [c["name"] for c in rt["columns"]]
            given = [c["target"] for c in rj["columns"]]
            for x in rcols:
                rep.check(given.count(x) == 1, f"{where}: rejects column '{x}' mapped {given.count(x)} times (need exactly 1)")
            for c in rj["columns"]:
                rep.check(c["target"] in rcols, f"{where}: rejects target '{c['target']}' is not a column of {rj['table']}")
                if "silver" in c:
                    rep.check(c["silver"] in cols, f"{where}: rejects column {c['target']} reads Silver column '{c['silver']}' that does not exist")
        for w in rj["when"]:
            rep.check(w["column"] in cols, f"{where}: reject rule on unknown Silver column '{w['column']}'")
rep.check(all(v == 1 for v in mapped.values()), f"mappings: a table is mapped by more than one file: {[k for k, v in mapped.items() if v > 1]}")
for p in files("fixtures/*.yaml"):
    fx = load_yaml(p)
    if fx.get("mapping"):
        rep.check((ROOT / fx["mapping"]).exists(), f"{rel(p)}: mapping {fx['mapping']} does not exist")

# ------------------------------------------------------------------ 8. fixtures point at real tables / columns
for p in files("fixtures/*.yaml"):
    fx = load_yaml(p)
    for tb in fx["input"]:
        rep.check(tb in known_tables, f"{rel(p)}: input table {tb} is not in tables/catalogue.yaml")
    for tb, rows_ in fx["expected"].items():
        rep.check(tb in known_tables, f"{rel(p)}: expected table {tb} is not in tables/catalogue.yaml")
        if tb in tables:
            cols = {c["name"] for c in tables[tb]["columns"]}
            for r in rows_:
                for c in r:
                    rep.check(c in cols, f"{rel(p)}: expected column {tb}.{c} does not exist")

rep.finish(f"{len(glossary)} terms, {len(classes)} classes, {len(tables)} table specs, {len(templates)} templates, "
           f"{len(contracts)} contracts, {len(assets)} assets, {len(kpis)} KPIs.")
