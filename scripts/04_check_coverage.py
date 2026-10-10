"""CHECK 4 - COVERAGE (task B2.5 "All 801 instances resolvable").
Expands every IIoT template x its machines into tag instances (UNS path, OPC node id, Kepware device/tag,
canonical asset id, measurement type) and compares them with the reference list from workbook v3
(tests/reference/tag_instances_v3.csv). Every reference instance must be produced exactly - no missing, no extra.
"""
import csv

from defs import ROOT, Report, files, load_yaml

rep = Report("04 coverage check")
assets = {a["machine_id"]: a for p in files("assets/*.yaml") for a in load_yaml(p)["assets"]}
produced = {}
for p in files("mappings/iiot/templates/*.yaml"):
    tp = load_yaml(p)
    pat = tp["patterns"]
    for m in tp["machines"]:
        a = assets[m]
        for t in tp["tags"]:
            v = {"process": a["process"], "line": a["line"], "machine": m, "domain": t["domain"], "tag": t["tag_name"]}
            v.update({f"{k}_lc": s.lower() for k, s in list(v.items())})
            produced[(m, t["tag_name"])] = {
                "canonical_asset_id": a["canonical_asset_id"], "uns_path": pat["uns_path"].format(**v),
                "opc_node_id": pat["opc_node_id"].format(**v), "kepware_device": pat["kepware_device"].format(**v),
                "kepware_tag": pat["kepware_tag"].format(**v), "measurement_type": t["measurement_type"].upper()}

with open(ROOT / "tests" / "reference" / "tag_instances_v3.csv", encoding="utf-8") as f:
    reference = {(r["machine_id"], r["tag_name"]): r for r in csv.DictReader(f)}

resolved = 0
for key, r in reference.items():
    got = produced.get(key)
    if not rep.check(got is not None, f"{key[0]}/{key[1]}: not produced by any template"):
        continue
    ok = True
    for field, val in got.items():
        ok &= rep.check(val == r[field], f"{key[0]}/{key[1]}: {field} = '{val}', reference says '{r[field]}'")
    resolved += ok
for key in produced:
    rep.check(key in reference, f"{key[0]}/{key[1]}: produced by a template but not in the reference list")
rep.finish(f"{resolved} / {len(reference)} reference tag instances resolved exactly; templates produce {len(produced)}.")
