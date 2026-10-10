# cantier-data-defs

Zone 07 of the Cantier AWS reference architecture: **the definition layer**.
Rule: **if it isn't in this repo, it doesn't exist.** Every table, column, ID, unit, rule and KPI the data platform
uses is written here first, reviewed by pull request, then published to AWS (Glue, DynamoDB, S3) by the pipeline (B5).

## Folders - what each one holds

| Folder | Holds | Task | Read by |
|---|---|---|---|
| `ontology/` | What things exist in the plant and how they connect (LinkML) | B2.1 | generators (B3.1), asset seeds |
| `glossary/` | Meaning, type, unit, valid values, owner of every term (measurements, entity ids, enums, columns) | B2.2 | tables, templates, contracts, S3 approved glossary |
| `contracts/` | Agreed shape of every event a producer sends (envelope + 4 events) | B2.3 | Glue Schema Registry (B5.2) |
| `tables/` | `catalogue.yaml` = every planned table; `<layer>/<table>.yaml` = full spec (columns, key, partition, owner) | B2.4 | Glue Data Catalog DDL (B3.2) |
| `mappings/iiot/templates/` | Tag list per machine type; machines x tags = the 801 tag instances | B2.5 | DynamoDB tag_map (B3.3) |
| `mappings/mes/` + `mes_catalogue.yaml` | One mapping per MES table (Bronze -> Silver: CDC, code maps, golden ids); catalogue of the 41 MES table groups | B2.6 | Silver engine (A3) |
| `mappings/iiot/streams/` | Mapping of an IIoT event stream to Silver (tag_map to measurement types, units, rejects) | B2.5 / B2.6 | Silver engine (A3) |
| `assets/` | Golden id of each machine + its MES / CMMS / IIoT / Kepware ids | B2.7 | DynamoDB identity_map (B3.4) |
| `dq/` | Data-quality rules per Silver / ops table | B2.8 | Glue Data Quality (B3.6) |
| `kpi/` | 52 KPI definitions: formula, grain, sources, owner | B2.9 | dbt Gold models (B3.7) |
| `fixtures/` | Small tests: Bronze rows in -> expected Silver rows out | B2.10 | engine tests (B4.4) |
| `schemas/` | JSON Schema per file type - the shape every file must have | B1.2 | `scripts/00` |
| `scripts/` | Checks that run on every pull request | B1.2 / B4 | CI |
| `tools/` | `import_workbook.py` - one-time bootstrap from workbook v3 (do not re-run) | B2 | - |
| `docs/` | **DEVELOPER_GUIDE.md** (how to build Bronze->Silver->Gold from this repo), **CANONICAL_STANDARDS.md**, versioning, branch protection, B2 status, findings | B1.3 / B1.4 | people |
| `tests/reference/` | The 801 tag instances from workbook v3 (coverage check reference) | B2.5 | `scripts/04` |

Top-level files: `release.yaml` (version of the whole definition set + `canonical_model_version`), `sources.yaml` (where Bronze comes from).

## Checks (run before every push; CI runs the same)

```powershell
python -m pip install -r requirements.txt
python scripts/00_validate_schemas.py      # every file has the right shape (JSON Schema)
python scripts/01_validate_ontology.py     # ontology is valid LinkML; assets pass linkml-validate
python scripts/03_validate_defs.py         # files agree with each other (terms, types, columns, ids)
python scripts/04_check_coverage.py        # templates rebuild all 801 tag instances exactly
python scripts/05_build_contracts.py       # contracts -> JSON Schema in build/contracts, sample event tested
python scripts/07_run_fixtures.py          # fixtures run through the reference engine (scripts/engine.py)
python scripts/06_check_versions.py --base origin/main   # version bumps follow docs/VERSIONING.md
```

## How a change gets in

1. Branch from `main` (`feature/<what>`).
2. Edit YAML. Bump the file's `version` and `release.yaml` (rules: `docs/VERSIONING.md`).
3. Run the checks above, push, open a pull request.
4. CI must be green; CODEOWNERS must approve (data steward for `ontology/` and `glossary/`).
5. Merge -> publish pipeline (B5) deploys to AWS.

## Definitions with real sample data

| Data | Bronze | Silver | Mapping | Fixture |
|---|---|---|---|---|
| MES customers (DMS) | `bronze.mes_cdc_customers` | `silver.mes_customer` | `mappings/mes/customers.yaml` | `fixtures/mes_customer_cdc.yaml` |
| IIoT tag events (Firehose) | `bronze.iiot_firehose_events` | `silver.iiot_tag_reading` (+ `ops.iiot_tag_reading_rejects`) | `mappings/iiot/streams/firehose_events.yaml` | `fixtures/iiot_firehose_reading.yaml` |

## Status
See `docs/B2_STATUS.md` for what is done, what is a draft, and what is waiting on decisions or source data.
