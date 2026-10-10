# Developer guide - building Bronze -> Silver (and Silver -> Gold) from these definitions

You do not hard-code table names, columns, units, codes or ids in the job. You read them from this repo
(today: the YAML files; after B3/B5: the published JSON in `s3://cantier-ref/mappings/vX.Y/`).

## 1. Which files you need for one Silver table

| You need | File | Example (customer) | Example (IIoT readings) |
|---|---|---|---|
| Where Bronze is | `sources.yaml`, `tables/bronze/*.yaml` | `bronze.mes_cdc_customers` | `bronze.iiot_firehose_events` |
| What to build | `tables/silver/<table>.yaml` (columns, types, key, partition) | `silver.mes_customer` | `silver.iiot_tag_reading` |
| How to fill each column | `mappings/mes/*.yaml` or `mappings/iiot/streams/*.yaml` | `mappings/mes/customers.yaml` | `mappings/iiot/streams/firehose_events.yaml` |
| Codes -> canonical values | glossary term `source_codes` | `is_active`, `vatability` | `signal_quality` |
| Machine golden ids | `assets/site01.yaml` (live: DynamoDB identity_map) | - | `Banbury01 -> AST-MIX-000001` |
| Units | glossary `unit` (+ tag_map `factor`) | - | `mixer_motor_power -> kW` |
| Row checks | `dq/<table>.yaml` | `dq/mes_customer.yaml` | `dq/iiot_tag_reading.yaml` |
| Test data in -> expected out | `fixtures/*.yaml` | `mes_customer_cdc.yaml` | `iiot_firehose_reading.yaml` |
| Reference behaviour | `scripts/engine.py` (run by `scripts/07_run_fixtures.py`) | | |

**Rule: your job is correct when it gives the same rows as the fixtures** (`python scripts/07_run_fixtures.py` shows the reference result).

## 2. Mapping keywords and the PySpark you write for them

Processing order per Bronze row: **cdc -> columns (from/value/generate -> transform -> lookup -> cast to table type) -> rejects -> DQ -> MERGE into Silver**.

| Keyword | Meaning | PySpark |
|---|---|---|
| `cdc: {key, order_by, op_column, delete_value}` | keep the latest change per key; drop keys whose latest change is a delete | `Window.partitionBy(key).orderBy(desc(order_by))`, `row_number()==1`, then `filter(op != 'D')`; MERGE on the table primary key |
| `from: c.Col` | copy Bronze column `Col` | `F.col("Col")` |
| `value: X` | constant (`null` allowed) | `F.lit(X)` |
| `generate: now` | processing time | `F.current_timestamp()` |
| `transform: trim / upper / lower` | text clean-up | `F.trim`, `F.upper(F.trim())`, `F.lower(F.trim())` |
| `transform: null_if {value}` | source value that means "no value" | `F.when(col == value, None).otherwise(col)` |
| `transform: to_utc {source_tz}` | parse and store as UTC | `F.to_utc_timestamp(F.to_timestamp(col), source_tz)` |
| `transform: to_timezone {tz}` | local wall-clock copy (e.g. IST) | `F.from_utc_timestamp(utc_col, tz)` |
| `transform: floor_minutes {minutes}` | window start | `F.window(utc_col, "5 minutes").start` or `date_trunc` + minute math |
| `transform: opc_segment {index}` | part of the OPC node id split by `.` | `F.element_at(F.split(col, "\\."), index)` |
| `transform: sha1 {inputs}` | deterministic id | `F.sha1(F.concat_ws("|", *inputs))` |
| `transform: unit_convert {inputs}` | value x tag_map `factor` (default 1) | broadcast join tag_map, multiply |
| `lookup: identity_map` | source id -> golden id (or `attribute`, e.g. `process`, `template`) | broadcast join of DynamoDB identity_map export (today: `assets/*.yaml`) |
| `lookup: code_map` | glossary `<term>.source_codes.<SYSTEM>` | small dict -> `F.create_map` or broadcast join |
| `lookup: tag_map` | stream tag -> glossary measurement type / unit | broadcast join (`mapping.tag_map` + glossary) |
| `rejects: {table, when, columns}` | first matching rule sends the row to the ops table with `reject_reason`, never to Silver | split the DataFrame with the same conditions, write rejects to `ops.*` |
| table `type` | cast after lookups | `bigint` -> `LongType`, `decimal(18,2)` -> `DecimalType(18,2)`, `timestamp` -> `TimestampType` (UTC) |
| `dq/<table>.yaml` | `error` rules reject the row, `warn` rules are counted | Glue Data Quality (DQDL from B3.6) or the same checks in Spark |

Always also write `_mapping_version` (from the mapping) and `canonical_model_version` (from `release.yaml`) so every Silver row says which definition produced it.

## 3. Silver -> Gold: are the same definitions used?

Yes - same repo, different files:

| Gold needs | File |
|---|---|
| KPI formula, grain, source Silver tables, owner | `kpi/*.yaml` (52 KPIs) |
| Gold table shape | `tables/gold/*.yaml` + `tables/catalogue.yaml` |
| Meaning of each column / unit | `glossary/*.yaml` |
| Tool | dbt Core + dbt-athena for KPI models (SQL), PySpark for the heavy ones (curing_cycle_health, pdm_feature_hourly, tyre_traceability) |

B3.7 will generate dbt model skeletons + tests from `kpi/*.yaml`; until then write the SQL from the `formula` and `grain` fields.

## 4. Run the checks before you push

```powershell
python -m pip install -r requirements.txt
python scripts/00_validate_schemas.py
python scripts/01_validate_ontology.py
python scripts/03_validate_defs.py
python scripts/04_check_coverage.py
python scripts/05_build_contracts.py
python scripts/07_run_fixtures.py
```
