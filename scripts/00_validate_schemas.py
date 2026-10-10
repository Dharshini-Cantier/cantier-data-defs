"""CHECK 0 - SHAPE (task B1.2): every definition file must match the JSON Schema of its folder.
A missing required field, a wrong type, an unknown key or a file in the wrong folder fails the check.
Runs on every pull request (.github/workflows/validate.yml).

  python scripts/00_validate_schemas.py            check every file
  python scripts/00_validate_schemas.py FILE ...   check only these files

ontology/ and assets/ are LinkML - they are checked by scripts/01_validate_ontology.py.
"""
import json
import sys
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator
from referencing import Registry, Resource

from defs import ROOT, Report, rel

SCHEMAS = ROOT / "schemas"
RULES = [  # (glob relative to repo root, schema name)
    ("release.yaml", "release"),
    ("sources.yaml", "sources"),
    ("glossary/*.yaml", "glossary"),
    ("contracts/*.yaml", "contract"),
    ("tables/catalogue.yaml", "catalogue"),
    ("tables/*/*.yaml", "table"),
    ("mappings/iiot/templates/*.yaml", "iiot_template"),
    ("mappings/mes_catalogue.yaml", "mes_catalogue"),
    ("mappings/mes/*.yaml", "mapping"),
    ("mappings/iiot/streams/*.yaml", "mapping"),
    ("dq/*.yaml", "dq"),
    ("kpi/*.yaml", "kpi"),
    ("fixtures/*.yaml", "fixture"),
]
LINKML = ("ontology/", "assets/")
SKIP_DIRS = {".git", ".github", ".venv", "venv", "data", "build", "docs", "schemas", "tests", "tools", "node_modules"}


def schema_for(r):
    for pattern, name in RULES:
        if Path(r).match(pattern) and r.count("/") == pattern.count("/"):
            return name
    return None


def main(argv):
    rep = Report("00 schema check")
    registry = Registry().with_resources(
        (p.name, Resource.from_contents(json.loads(p.read_text(encoding="utf-8")))) for p in SCHEMAS.glob("*.schema.json"))
    validators = {}
    paths = [Path(a).resolve() for a in argv] if argv else sorted(
        p for p in ROOT.rglob("*.y*ml") if not SKIP_DIRS & set(p.relative_to(ROOT).parts))
    checked = 0
    for path in paths:
        r = rel(path)
        if r.startswith(LINKML):
            continue
        name = schema_for(r)
        if not rep.check(name is not None, f"{r}: no schema covers this location - put the file in the right folder"):
            continue
        try:
            doc = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            rep.check(False, f"{r}: not valid YAML - {e}")
            continue
        if name not in validators:
            validators[name] = Draft202012Validator(json.loads((SCHEMAS / f"{name}.schema.json").read_text(encoding="utf-8")), registry=registry)
        checked += 1
        errs = sorted(validators[name].iter_errors(doc), key=lambda e: list(e.absolute_path))
        rep.check(not errs, f"{r}: {len(errs)} schema error(s)")
        for e in errs[:10]:
            where = "/".join(str(x) for x in e.absolute_path) or "(top level)"
            rep.errors.append(f"{r} [{name}] at {where}: {e.message[:200]}")
    rep.finish(f"{checked} file(s) checked against schemas/.")


if __name__ == "__main__":
    main(sys.argv[1:])
