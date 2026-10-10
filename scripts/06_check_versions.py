"""CHECK 6 - VERSIONS (task B1.3, rules from docs/VERSIONING.md). Compares changed definition files with a base
branch and fails when:
  - a definition file changed but its `version` did not go up
  - a BREAKING change (removed column / field / term / tag, changed type or unit, changed primary key, new required
    contract field) has only a PATCH bump (0.x: needs at least MINOR; from 1.0.0: needs MAJOR or a new _v2 table/contract)
  - an IIoT template changed tags but kept its mapping_version
  - any definition changed but release.yaml version did not go up

  python scripts/06_check_versions.py --base origin/main      (CI uses the pull request target branch)
"""
import argparse
import subprocess

import yaml

from defs import ROOT, Report

DEF_DIRS = ("ontology/", "glossary/", "contracts/", "tables/", "mappings/", "assets/", "dq/", "kpi/", "fixtures/")


def git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, encoding="utf-8")


def ver(v):
    return tuple(int(x) for x in str(v).split("."))


def bump_kind(old, new):
    o, n = ver(old), ver(new)
    if n <= o:
        return None
    return "major" if n[0] > o[0] else "minor" if n[1] > o[1] else "patch"


def breaking(path, old, new):
    """Return a list of breaking changes between two versions of a file."""
    out = []
    if path.startswith("tables/") and "columns" in old:
        oc, nc = {c["name"]: c for c in old["columns"]}, {c["name"]: c for c in new["columns"]}
        out += [f"column {c} removed" for c in oc if c not in nc]
        out += [f"column {c} type {oc[c]['type']} -> {nc[c]['type']}" for c in oc if c in nc and oc[c]["type"] != nc[c]["type"]]
        if old.get("primary_key") != new.get("primary_key"):
            out.append("primary key changed")
    if path.startswith("glossary/"):
        ot, nt = old["terms"], new["terms"]
        out += [f"term {k} removed" for k in ot if k not in nt]
        out += [f"term {k} data_type changed" for k in ot if k in nt and ot[k]["data_type"] != nt[k]["data_type"]]
        out += [f"term {k} unit changed" for k in ot if k in nt and ot[k].get("unit") != nt[k].get("unit")]
    if path.startswith("contracts/"):
        of, nf = {f["name"]: f for f in old["fields"]}, {f["name"]: f for f in new["fields"]}
        out += [f"field {k} removed" for k in of if k not in nf]
        out += [f"field {k} type changed" for k in of if k in nf and of[k]["type"] != nf[k]["type"]]
        out += [f"new required field {k}" for k in nf if k not in of and nf[k]["required"]]
    if path.startswith("mappings/iiot/"):
        ot, nt = {t["tag_name"]: t for t in old["tags"]}, {t["tag_name"]: t for t in new["tags"]}
        out += [f"tag {k} removed" for k in ot if k not in nt]
        out += [f"tag {k} unit changed" for k in ot if k in nt and ot[k].get("unit") != nt[k].get("unit")]
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base", default="origin/main")
    a = ap.parse_args()
    rep = Report(f"06 version check (against {a.base})")
    if git("rev-parse", "--verify", a.base).returncode != 0:
        print(f"Base '{a.base}' not found - nothing to compare (first commit?). OK")
        return
    changed = [l.split("\t") for l in git("diff", "--name-status", a.base, "--", *DEF_DIRS, "release.yaml").stdout.splitlines()]
    any_def = False
    for status, *paths in changed:
        path = paths[-1]
        if not path.endswith(".yaml"):
            continue
        if path != "release.yaml":
            any_def = True
        if status.startswith("A") or status.startswith("D"):
            continue
        old = yaml.safe_load(git("show", f"{a.base}:{path}").stdout)
        new = yaml.safe_load((ROOT / path).read_text(encoding="utf-8"))
        if not isinstance(old, dict) or "version" not in old:
            continue
        kind = bump_kind(old["version"], new["version"])
        if not rep.check(kind is not None, f"{path}: changed but version stayed {new['version']} - bump it (docs/VERSIONING.md)"):
            continue
        br = breaking(path, old, new)
        if br:
            need = "major" if ver(old["version"])[0] >= 1 else "minor"
            ok = kind == "major" or (need == "minor" and kind == "minor")
            rep.check(ok, f"{path}: BREAKING ({'; '.join(br)}) needs a {need.upper()} bump, got {kind}")
        if path.startswith("mappings/iiot/") and old.get("tags") != new.get("tags"):
            rep.check(old.get("mapping_version") != new.get("mapping_version"), f"{path}: tags changed - set a new mapping_version")
    if any_def:
        rel_old = yaml.safe_load(git("show", f"{a.base}:release.yaml").stdout or "{}") or {}
        rel_new = yaml.safe_load((ROOT / "release.yaml").read_text(encoding="utf-8"))
        if rel_old.get("version"):
            rep.check(bump_kind(rel_old["version"], rel_new["version"]) is not None, "release.yaml: definitions changed - bump the release version and add a changes entry")
    rep.finish(f"{len(changed)} changed file(s) compared.")


if __name__ == "__main__":
    main()
