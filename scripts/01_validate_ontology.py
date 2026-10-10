"""CHECK 1 - ONTOLOGY (task B2.1 "linkml-validate passes", B2.7 asset seeds).
  1. ontology/manufacturing.yaml loads as a valid LinkML schema (every range / class it names exists)
  2. it can be generated into JSON Schema (proves it is usable by the B3.1 generators)
  3. every assets/*.yaml file validates against the ontology class AssetRegistry
     (same as:  linkml-validate -s ontology/manufacturing.yaml -C AssetRegistry assets/site01.yaml)
Needs:  pip install linkml
"""
import sys

from defs import ROOT, Report, files, load_yaml, rel

rep = Report("01 ontology check (LinkML)")
try:
    from linkml.generators.jsonschemagen import JsonSchemaGenerator
    from linkml.validator import validate
    from linkml_runtime.utils.schemaview import SchemaView
except ImportError:
    print("linkml is not installed. Run:  python -m pip install linkml")
    sys.exit(1)

schema_path = ROOT / "ontology" / "manufacturing.yaml"
sv = SchemaView(str(schema_path))
classes = sv.all_classes()
known = set(classes) | set(sv.all_enums()) | set(sv.all_types())
n_rel = 0
for cname in classes:
    for s in sv.class_induced_slots(cname):
        ranges = [x.range for x in s.any_of] if s.any_of else [s.range]
        for r in ranges:
            rep.check(r in known, f"class {cname}.{s.name}: range '{r}' is not a class, enum or type")
        if cname != "AssetRegistry" and any(r in classes for r in ranges):
            n_rel += 1
    rep.check(bool(sv.get_class(cname).description), f"class {cname}: description missing")

try:
    JsonSchemaGenerator(str(schema_path), top_class="AssetRegistry").serialize()
    rep.check(True, "")
except Exception as e:  # noqa: BLE001
    rep.check(False, f"JSON Schema generation failed: {e}")

n_assets = 0
for p in files("assets/*.yaml"):
    data = load_yaml(p)
    report = validate(data, str(schema_path), target_class="AssetRegistry")
    for res in report.results:
        rep.check(False, f"{rel(p)}: {res.message}")
    rep.check(True, "")
    ids = [a["canonical_asset_id"] for a in data.get("assets", [])]
    n_assets += len(ids)
    rep.check(len(ids) == len(set(ids)), f"{rel(p)}: duplicate canonical_asset_id")
    machines = [a["machine_id"] for a in data.get("assets", [])]
    rep.check(len(machines) == len(set(machines)), f"{rel(p)}: duplicate machine_id")
    for a in data.get("assets", []):
        want = f"tyreplant01/{a['process'].lower()}/{a['line'].lower()}/{a['machine_id'].lower()}"
        rep.check(a["uns_base_path"] == want, f"{rel(p)} {a['machine_id']}: uns_base_path should be {want}")
        rep.warn(a["mapping_status"] != "PROPOSED", f"{a['machine_id']}: ids are PROPOSED patterns - replace with real MES/CMMS ids (B2.7)")

rep.finish(f"{len(classes) - 1} classes, {n_rel} relation slots, {n_assets} assets validated with linkml.", max_warnings=3)
