## What changes
<!-- one or two lines: which definitions and why -->

## Kind of change (docs/VERSIONING.md)
- [ ] PATCH - wording only
- [ ] MINOR - additive (new column / term / tag / KPI / optional field)
- [ ] MAJOR - breaking (removed / renamed / type or unit change / new required field / key change)

## Checklist
- [ ] `version` bumped in every changed file
- [ ] `release.yaml` version bumped + `changes` entry
- [ ] `mapping_version` changed if tags, units, lookups or CDC rules changed
- [ ] all checks green locally (`scripts/00` ... `06`)
- [ ] source of the change linked (workbook row, MES schema export, ticket)
