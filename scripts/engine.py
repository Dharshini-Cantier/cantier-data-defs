"""REFERENCE Bronze -> Silver engine: executes one mapping file (mappings/mes/*.yaml, mappings/iiot/streams/*.yaml)
on a list of Bronze rows. It exists to PROVE the definitions are complete (scripts/07 runs the fixtures through it)
and to show the Bronze->Silver developer exactly what each mapping keyword means.
The production job is PySpark (Track A3) and must give the same output - see docs/DEVELOPER_GUIDE.md.
"""
import datetime as dt
import hashlib
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from defs import ROOT, files, load_yaml

UTC = dt.timezone.utc


def load_glossary():
    return {k: v for p in files("glossary/*.yaml") for k, v in load_yaml(p)["terms"].items()}


def load_identity_map(given=None):
    """(source_system, source_type, source_id) -> {"id": canonical id, ...attributes}. Assets come from assets/*.yaml
    (the live copy is DynamoDB identity_map, B3.4); fixtures can add rows (e.g. golden customer ids from MDM)."""
    out = {}
    for p in files("assets/*.yaml"):
        for a in load_yaml(p)["assets"]:
            rec = {"id": a["canonical_asset_id"], **a}
            out[("CANTIER_IIOT", "asset", a["machine_id"])] = rec
            if a.get("mes_asset_id"):
                out[("MES_CORE", "asset", a["mes_asset_id"])] = rec
            if a.get("cmms_asset_id"):
                out[("CMMS", "asset", a["cmms_asset_id"])] = rec
    for g in (given or []):
        sid = str(g.get("source_id", g.get("source_asset_id")))
        out[(g["source_system"], g.get("source_type", "asset"), sid)] = {"id": g.get("canonical_id", g.get("canonical_asset_id"))}
    return out


def parse_ts(v, source_tz="UTC"):
    if v is None or v == "":
        return None
    if isinstance(v, dt.datetime):
        t = v
    else:
        t = dt.datetime.fromisoformat(str(v).replace("Z", "+00:00"))
    if t.tzinfo is None:
        t = t.replace(tzinfo=ZoneInfo(source_tz))
    return t.astimezone(UTC)


def fmt_ts(t):
    if t is None:
        return None
    s = t.strftime("%Y-%m-%d %H:%M:%S")
    if t.microsecond:
        s += f".{t.microsecond:06d}".rstrip("0")
    return s


def col(row, ref):
    return row.get(ref.split(".", 1)[1])


class Engine:
    def __init__(self, mapping, given=None):
        self.m = mapping
        self.glossary = load_glossary()
        self.idmap = load_identity_map(given)
        self.tables = {load_yaml(p)["name"]: load_yaml(p) for p in files("tables/*/*.yaml") if p.name != "catalogue.yaml"}
        self.target = self.tables[mapping["target_table"]]
        self.system = mapping["source"].get("system")

    # ---------------------------------------------------------------- building blocks
    def cdc(self, rows):
        c = self.m.get("cdc")
        if not c:
            return rows
        keys = [k.split(".", 1)[1] for k in c["key"]]
        order, op = c["order_by"].split(".", 1)[1], c["op_column"].split(".", 1)[1]
        latest = {}
        for r in sorted(rows, key=lambda r: parse_ts(r.get(order))):
            latest[tuple(r.get(k) for k in keys)] = r
        return [r for r in latest.values() if r.get(op) != c.get("delete_value", "D")]

    def lookup(self, value, lk):
        if value is None:
            return None
        if lk["map"] == "identity_map":
            rec = self.idmap.get((lk["source_system"], lk["source_type"], str(value)))
            return None if rec is None else rec.get(lk.get("attribute", "id"))
        if lk["map"] == "code_map":
            codes = self.glossary[lk["source_type"]].get("source_codes", {}).get(lk["source_system"], {})
            return codes.get(str(value), codes.get(value))
        if lk["map"] == "tag_map":
            t = (self.m.get("tag_map") or {}).get(value)
            if t is None:
                return None
            term = self.glossary[t["measurement_type"]]
            return {"measurement_type": term.get("measurement_type", t["measurement_type"].upper()), "unit": term.get("unit")}.get(lk.get("attribute", "measurement_type"))
        raise ValueError(f"unknown map {lk['map']}")

    def transform(self, value, tr, row):
        fn = tr["fn"]
        if fn == "sha1":
            return hashlib.sha1("|".join(str(col(row, i)) for i in tr["inputs"]).encode()).hexdigest()
        if value is None:
            return None
        if fn == "trim":
            return str(value).strip()
        if fn == "upper":
            return str(value).strip().upper()
        if fn == "lower":
            return str(value).strip().lower()
        if fn == "null_if":
            return None if str(value) == str(tr["value"]) else value
        if fn == "to_utc":
            return parse_ts(value, tr.get("source_tz", "UTC"))
        if fn == "to_timezone":  # local wall-clock time in tz, stored without zone
            return parse_ts(value, tr.get("source_tz", "UTC")).astimezone(ZoneInfo(tr["tz"])).replace(tzinfo=UTC)
        if fn == "floor_minutes":
            t = parse_ts(value, tr.get("source_tz", "UTC"))
            return t.replace(minute=t.minute - t.minute % tr["minutes"], second=0, microsecond=0)
        if fn == "opc_segment":
            return str(value).split(".")[tr["index"]]
        if fn == "unit_convert":
            t = (self.m.get("tag_map") or {}).get(col(row, tr["inputs"][0])) or {}
            return float(value) * t.get("factor", 1.0)
        raise ValueError(f"unknown transform {fn}")

    def cast(self, value, typ):
        if value is None:
            return None
        if typ in ("int", "bigint"):
            return int(value)
        if typ == "double":
            return float(value)
        if typ.startswith("decimal"):
            return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
        if typ == "boolean":
            return value if isinstance(value, bool) else str(value).lower() in ("true", "1")
        if typ == "timestamp":
            return fmt_ts(value if isinstance(value, dt.datetime) else parse_ts(value))
        return str(value)

    # ---------------------------------------------------------------- run
    def run(self, raw):
        """raw = {bronze table: [rows]} -> (silver rows, reject rows)"""
        alias, table = next(iter(self.m["source"]["tables"].items()))
        rows = self.cdc(raw.get(table, []))
        types = {c["name"]: c["type"] for c in self.target["columns"]}
        silver, rejects = [], []
        for r in rows:
            out = {}
            for c in self.m["columns"]:
                if "generate" in c:
                    v = "NOW"
                elif "value" in c:
                    v = c["value"]
                elif "from" in c:
                    v = col(r, c["from"])
                else:
                    v = None
                if "transform" in c:
                    v = self.transform(v, c["transform"], r)
                if "lookup" in c:
                    v = self.lookup(v, c["lookup"])
                out[c["target"]] = v if c.get("generate") else self.cast(v, types[c["target"]])
            reason = self.reject_reason(out)
            if reason:
                rejects.append(self.reject_row(r, out, reason))
            else:
                silver.append(out)
        return silver, rejects

    def reject_reason(self, out):
        rj = self.m.get("rejects")
        for w in (rj or {}).get("when", []):
            v = out.get(w["column"])
            if (w["test"] == "is_null" and v is None) or (w["test"] == "not_equal" and v != w["value"]):
                return w["reason"]
        return None

    def reject_row(self, r, out, reason):
        row = {}
        for c in self.m["rejects"]["columns"]:
            if c.get("generate") == "reason":
                row[c["target"]] = reason
            elif c.get("generate") == "now":
                row[c["target"]] = "NOW"
            elif "silver" in c:
                row[c["target"]] = out.get(c["silver"])
            else:
                v = col(r, c["from"])
                row[c["target"]] = None if v is None else str(v)
        return row
