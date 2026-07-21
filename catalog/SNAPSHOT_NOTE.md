# Registry snapshot — canonical (2026-07-21)

`MFL_Dataset_Registry.xlsx` in this folder is the **canonical registry snapshot**,
committed so the pipeline and CI are self-contained and reproducible.

- 68 records, unique literal Record IDs (`MFL-2026-001` … `MFL-2026-069`; ID
  formulas were removed on 2026-07-21 — see `docs/REGISTRY_CHANGELOG_2026-07-21.md`).
- The **Living landscape** column uses the canonical controlled list approved by
  Lizeth on 2026-07-21: 11 delineated landscapes (see `boundaries/`) plus
  `NATIONAL — Country-wide coverage` and `GLOBAL — Global / cross-landscape`.
  The full table lives in the workbook's *Reference* sheet (columns K–M).
- `PER-PCL` (Pucallpa – Ucayali) is **pending confirmation** with the Peru team.

To update: edit this file (new rows type the next free `MFL-2026-###` ID manually),
then run `./scripts/regenerate.sh`. Working copies received from focal points
(e.g. `MFL_Dataset_Registry 21jul.xlsx`) stay local and are git-ignored.
