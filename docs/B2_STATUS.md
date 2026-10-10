# Track B status - B1 (repo & standards) and B2 (content authoring)

Source: `Cantier_Tyre_Datapoints_Ontology_Medallion_Catalogue_v3.xlsx` (workbook v3) + `Cantier_Data_Platform_Task_Plan.xlsx`.
All definition files are `version: 0.1.0` drafts until reviewed. Every check in `scripts/` passes.

## B1 - Repo & standards

| Task | Done when (plan) | In the repo | Still needed |
|---|---|---|---|
| B1.1 Repo + layout | Repo + README merged | Full folder layout, README with folder guide, local Git with one commit per task | Push to the company GitHub, merge to `main` |
| B1.2 YAML schemas | Invalid YAML fails CI | 13 JSON Schemas (`schemas/`), `scripts/00_validate_schemas.py`, LinkML check for ontology + assets, CI workflow. Tested: a broken term fails with exit code 1 | First green run in GitHub Actions |
| B1.3 Versioning policy | Documented + approved | `docs/VERSIONING.md` (semver, canonical_model_version, mapping_version, additive vs breaking) + `scripts/06_check_versions.py` enforces it | Steward + DE sign-off in the doc |
| B1.4 Branch protection + CODEOWNERS | Enforced on main | `.github/CODEOWNERS` (steward owns ontology/glossary), PR template, `docs/BRANCH_PROTECTION.md` | Real GitHub usernames in CODEOWNERS; admin turns protection on |

## B2 - Content authoring

| Task | Done when (plan) | In the repo | Still needed (who) |
|---|---|---|---|
| B2.1 Ontology | linkml-validate passes | `ontology/manufacturing.yaml` - LinkML, 40 classes + 41 relations (sheets 09/10), relations as attributes with cardinality. `scripts/01` loads it, generates JSON Schema, validates assets | Steward review (STW) |
| B2.2 Glossary | Unit fixes applied; ranges present | 173 measurement types (03-06), 10 unit fixes recorded as `source_unit`, 113 with physical ranges, 21 marked `missing_at_source`, 17 `derived` (Prod_* not ingested). Machine_State / Cure_PressStatus changed to string enums (finding). Plus 46 entity, 6 enum and 197 column terms | **Plant limits** - not in any source (Variable Master empty): come from `silver.mdm_spec_limit` once decision 0.4 loads them. Confirm owners (STW + IIoT) |
| B2.3 Contracts | Schemas generated + reviewed | envelope.v1, iiot.reading.v1, curing.condition.v2, mes.lot_action.v1, qa.inspection.v1. `scripts/05` generates JSON Schema to `build/contracts/` and tests a sample event | DE review |
| B2.4 Table specs | Every column has term or technical | 33 full specs (412 columns: 355 with a glossary term, 57 technical) + `tables/catalogue.yaml` with all 171 planned tables (17 were referenced in the workbook but missing from sheet 12) | ~120 tables have no columns yet: MES Silver tables need the MES schema export (B2.6); Gold tables need AN design. Review chosen primary keys |
| B2.5 IIoT templates | All 801 instances resolvable | 8 templates; `scripts/04` rebuilds **801 / 801** tag instances exactly (UNS path, OPC node, Kepware device + tag, canonical asset, measurement type) | Split the Utility template (finding); add SteamValve CMD/FB to Curing when published |
| B2.6 MES mappings | Covers all A3.11 tables | `mappings/mes_catalogue.yaml` - 41 MES table groups. **Customers done** from the real DMS sample: Bronze spec, `silver.mes_customer`, `mappings/mes/customers.yaml` (CDC, code maps, golden id), DQ, fixture. IIoT Firehose stream mapped to `silver.iiot_tag_reading` (`mappings/iiot/streams/firehose_events.yaml`) | Remaining MES tables as parquet samples / schema export arrive. Decision 0.2 |
| B2.7 Asset seeds | Real IDs replace placeholders | `assets/site01.yaml` - 21 machines, validated with linkml-validate | Real MES + CMMS ids (all `PROPOSED`). Plan says 22 machines, workbook has 21 - confirm |
| B2.8 DQ rules | Generated rulesets valid | 15 files (every Silver + ops spec): key unique/not null, enum values, physical ranges, asset id format, time order, qty out <= in, LSL <= target <= USL, GOOD-only readings | Tune severities with owners. DQDL is B3.6 |
| B2.9 KPIs | Matches KPI list | 52 / 52 KPIs in 8 area files with formula, grain, MES source tables -> Silver sources, Gold table | Confirm owners (area names used) |
| B2.10 Fixtures | Fixtures reviewed | 7 fixtures; **mes_customer_cdc and iiot_firehose_reading run green through the reference engine** (`scripts/07`); the other 5 wait for their mappings | DE review |

## Decisions that block finishing B2 (Track 0)

| Decision | Blocks |
|---|---|
| 0.1 cycle_id = MES LotActions.Id on UNS | contracts mes.lot_action / curing.condition, fixtures |
| 0.2 CMMS inside the MES DB? | B2.6 source list, B2.7 CMMS ids |
| 0.4 spec limits home | B2.2 plant ranges, silver.mdm_spec_limit |

## Source findings
`docs/FINDINGS.md` lists the 20 findings from workbook sheet 01 (fix before schema freeze).
