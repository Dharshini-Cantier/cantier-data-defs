"""CHECK 5 - CONTRACTS (task B2.3 "Schemas generated"): turn every contracts/*.yaml into a JSON Schema in
build/contracts/<id>.schema.json (envelope fields merged in for events) and test it with a sample event built from
the envelope examples. build/ is not committed - the B5.2 publish step registers these in Glue Schema Registry.
"""
import json

from jsonschema import Draft202012Validator

from defs import ROOT, Report, files, load_yaml

rep = Report("05 contract build")
JSON_TYPE = {"string": {"type": "string"}, "int": {"type": "integer"}, "bigint": {"type": "integer"}, "double": {"type": "number"},
             "boolean": {"type": "boolean"}, "date": {"type": "string", "format": "date"}, "timestamp": {"type": "string", "format": "date-time"},
             "array<string>": {"type": "array", "items": {"type": "string"}}, "any": {"type": ["string", "number", "boolean"]}}
glossary = {k: v for p in files("glossary/*.yaml") for k, v in load_yaml(p)["terms"].items()}
contracts = {load_yaml(p)["id"]: load_yaml(p) for p in files("contracts/*.yaml")}
out_dir = ROOT / "build" / "contracts"
out_dir.mkdir(parents=True, exist_ok=True)


def all_fields(c):
    """Parent (envelope) fields first; a child field with the same name replaces the parent's."""
    merged = {f["name"]: f for f in (all_fields(contracts[c["extends"]]) if c.get("extends") else [])}
    merged.update({f["name"]: f for f in c["fields"]})
    return list(merged.values())


for cid, c in contracts.items():
    props, required = {}, []
    for f in all_fields(c):
        p = dict(JSON_TYPE[f["type"]])
        term = glossary.get(f.get("term") or "")
        if term and term.get("enum_values"):
            p["enum"] = list(term["enum_values"])
        if f.get("description"):
            p["description"] = f["description"]
        if f.get("term"):
            p["x-glossary-term"] = f["term"]
        if f.get("pii"):
            p["x-pii"] = True
        props[f["name"]] = p
        if f["required"]:
            required.append(f["name"])
    if c.get("allowed_tags"):
        props["tag_name"] = {**props.get("tag_name", {"type": "string"}), "enum": c["allowed_tags"]}
    schema = {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": f"{cid}.schema.json", "title": cid,
              "description": c["description"], "type": "object", "properties": props, "required": required,
              "x-contract-version": c["version"], "x-compatibility": c["compatibility"]}
    if c.get("topic"):
        schema["x-topic"] = c["topic"]
    Draft202012Validator.check_schema(schema)
    (out_dir / f"{cid}.schema.json").write_text(json.dumps(schema, indent=2, ensure_ascii=False), encoding="utf-8")
    rep.check(True, "")

# sample event: the envelope examples (sheet 02) must pass the iiot.reading.v1 schema
env = contracts["envelope.v1"]
sample = {f["name"]: f["example"] for f in env["fields"] if f.get("example")}
sample.update({"tag_name": "Bearing_Temperature", "metric_value": 54.7, "quality": "GOOD", "source_system": "CANTIER_IIOT", "plant_asset_id": "CuringPress01",
               "site": "Site01", "process": "Curing", "line": "CuringLine01", "machine": "CuringPress01", "mapping_id": "1"})
schema = json.loads((out_dir / "iiot.reading.v1.schema.json").read_text(encoding="utf-8"))
errs = list(Draft202012Validator(schema).iter_errors(sample))
for e in errs:
    rep.check(False, f"sample iiot.reading.v1 event: {e.message}")
rep.check(not errs, "")
bad = dict(sample, quality="MAYBE")
rep.check(any(True for _ in Draft202012Validator(schema).iter_errors(bad)), "a wrong quality value should be rejected by the contract")
rep.finish(f"{len(contracts)} JSON Schemas written to build/contracts/, sample event valid, bad event rejected.")
