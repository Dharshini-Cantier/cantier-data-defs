# Versioning policy (task B1.3)

> Status: **DRAFT - for approval by the data steward (STW) and data engineering (DE).**
> Enforced by `scripts/06_check_versions.py` on every pull request.

## 1. Three version numbers

| Number | Where | Meaning |
|---|---|---|
| `version` (semver `MAJOR.MINOR.PATCH`) | every definition file + `release.yaml` | version of that file / of the whole set |
| `canonical_model_version` (`manufacturing-vX.Y`) | `release.yaml`, ontology annotation, Silver column | version of the canonical model data was conformed to |
| `mapping_version` (`iiot-map-YYYY.MM.DD`, `mes-map-YYYY.MM.DD`) | IIoT templates, MES mappings, asset seeds | which mapping produced a Silver row (stored in `_mapping_version`) |

## 2. What kind of change is it?

| Change | Kind | Examples |
|---|---|---|
| Wording only - no change to data or meaning | **PATCH** | fix a description, an owner name |
| **Additive** - old consumers keep working | **MINOR** | new nullable column, new term, new tag, new KPI, new optional contract field |
| **Breaking** - old consumers may break or give wrong numbers | **MAJOR** | remove/rename a column, term, tag or field; change a type or unit; change a primary key; new *required* contract field |

While a file is `0.x.y` (draft), a breaking change needs at least a **MINOR** bump. From `1.0.0` (in production) it needs **MAJOR**.

## 3. Breaking changes in production (1.x)

- **Tables:** do not change the existing table - create `<table>_v2`, run both, migrate consumers, deprecate v1 (`status: deprecated`).
- **Contracts:** new contract id with the next major (`curing.condition.v3`); compatibility mode stays `BACKWARD`.
- **Glossary units:** a unit change is breaking - add a new term or convert in Silver; never silently change history.

## 4. Mapping versions

- Any change to tags, units, lookups or CDC rules -> new `mapping_version`.
- Silver writes `_mapping_version` on every row; DynamoDB keeps old versions (`mappingVersion`) so rows can be replayed.

## 5. Every pull request

1. Bump `version` of each changed file (CI fails otherwise).
2. Bump `release.yaml` `version` and add a `changes` entry.
3. Bump `canonical_model_version` when ontology classes / relations change.

## Approval

| Role | Name | Date |
|---|---|---|
| Data steward (STW) | | |
| Data engineering (DE) | | |
