# Canonical standards - what "canonical" means in this repo

"Canonical" = the one agreed way to name, type, measure, code and identify data in Silver and Gold, no matter which
source it came from. These are the team's 5 standards (from the Bronze -> Silver standards note) and where each one
is written down and checked here.

| # | Standard | Rule | Written in | Checked by |
|---|---|---|---|---|
| 1 | Standard column names | Raw abbreviations become plain English snake_case (`CustomerCode` -> `customer_code`, `mch_id` -> `machine_id`). Bronze keeps source names; Silver/Gold never do | `tables/silver|gold/*.yaml` + `mappings/` (`target` <- `from`) | `03`: every Silver/Gold/ops column is snake_case and has a glossary term or `technical: true` |
| 2 | Standard data types | Source ids `bigint` (e.g. `customer_id`), money `decimal(18,2)`, flags `boolean`, all timestamps **UTC** (`*_utc`, `event_ts_utc`); IST only as an extra column | `glossary/*.yaml` `data_type`, table `type` | `03`: table type = glossary type; mapping transform `to_utc` |
| 3 | Standard units (UOM) | One canonical unit per measurement type: temperature °C, weight kg, length mm, pressure bar, power kW. Source unit + factor are kept for conversion | `glossary/measurement_types.yaml` `unit`, `source_unit`; stream `tag_map` `source_unit` + `factor` | `03`: template unit = glossary unit; tag_map with `source_unit` needs a `factor`; fixture `unit_conversion` |
| 4 | Standard status codes (enums) | Legacy codes (`'A'`, `'1'`, `'true'`, `'Y'`) become one boolean (`is_active`) or one closed list (`GOOD/UNCERTAIN/BAD`, `NON_VATABLE` ...) | glossary term `enum_values` + `source_codes.<SYSTEM>` (the code map) | `03`: every `code_map` lookup has `source_codes` for that system and maps only to allowed values; DQ `accepted_values` |
| 5 | Entity identifiers (golden ids) | Local ids resolve to one enterprise id: machines `AST-<TYPE>-<6 digits>`, customers `GOLDEN_CUST_<n>` | `glossary/entities.yaml` (pattern), `assets/*.yaml` (machine crosswalk), identity_map lookups in mappings | `01` (asset ids, linkml), DQ pattern rules, fixtures |

## How a Bronze value becomes canonical (example: one customer)

| Bronze (MES, as DMS wrote it) | Rule | Silver (canonical) |
|---|---|---|
| `Id = 1` | name + type | `customer_id = 1` (bigint) |
| `CustomerCode = "cust-us-001 "` | name + `upper` | `customer_code = "CUST-US-001"` |
| `IsActive = "true"` | code map `is_active.source_codes.MES_CORE` | `is_active = true` |
| `Vatability = "NonVatable"` | code map `vatability` | `vatability = "NON_VATABLE"` |
| `SalesPersonId = 0` | `null_if 0` | `sales_person_id = null` |
| `AddedDate = 2026-10-07 01:01:32.499 (UTC)` | `to_utc` | `created_at_utc = 2026-10-07 01:01:32.499` |
| `Id = 1` via identity_map | golden id | `golden_customer_id = GOLDEN_CUST_1001` |

## Open items against the standards (need the data steward)

- Glossary units `m (or kg)` on 3 cord / bead-wire tags - decide one unit (workbook finding).
- `kN` (one tag) and `g·cm` (dynamic balance) are not converted to N / standard units yet.
- `business_partner_type_code` and `transport_time` meanings / unit to confirm with MES.
- Golden customer ids come from entity resolution / MDM (B7); until then `golden_customer_id` is null (DQ warning).
