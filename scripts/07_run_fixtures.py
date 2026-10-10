"""CHECK 7 - FIXTURES (B2.10 / B4.4): every fixture that names a `mapping` is run through the reference engine
(scripts/engine.py). Each expected row must match one produced row on every column it lists, and the number of
rows per table must be equal. Fixtures without a mapping (mapping not written yet) are listed as pending.
"""
from defs import ROOT, Report, files, load_yaml, rel
from engine import Engine

rep = Report("07 fixture tests")


def same(a, b):
    if a is None or b is None:
        return a is None and b is None
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or str(a).lower() == str(b).lower()
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return abs(a - b) < 1e-9
    return str(a) == str(b)


ran, pending = 0, []
for p in files("fixtures/*.yaml"):
    fx = load_yaml(p)
    if not fx.get("mapping"):
        pending.append(fx["name"])
        continue
    engine = Engine(load_yaml(ROOT / fx["mapping"]), (fx.get("given") or {}).get("identity_map"))
    silver, rejects = engine.run(fx["input"])
    produced = {engine.m["target_table"]: silver}
    if engine.m.get("rejects"):
        produced[engine.m["rejects"]["table"]] = rejects
    ok = True
    for table, expected in fx["expected"].items():
        got = list(produced.get(table, []))
        ok &= rep.check(len(got) == len(expected), f"{rel(p)}: {table} expected {len(expected)} rows, engine produced {len(got)}")
        for e in expected:
            hit = next((g for g in got if all(same(g.get(k), v) for k, v in e.items())), None)
            if hit is None:
                close = min(got, key=lambda g: sum(not same(g.get(k), v) for k, v in e.items()), default={})
                diff = {k: (v, close.get(k)) for k, v in e.items() if not same(close.get(k), v)}
                ok &= rep.check(False, f"{rel(p)}: {table} no row matches {e} - closest differs on (expected, got) {diff}")
            else:
                got.remove(hit)
    print(f"  {'PASS' if ok else 'FAIL'}  {fx['name']}: {len(silver)} Silver row(s), {len(rejects)} reject(s)")
    ran += 1
rep.finish(f"{ran} fixture(s) run through the reference engine; pending (mapping not written yet): {', '.join(pending) or 'none'}.")
