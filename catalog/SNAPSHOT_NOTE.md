# Registry Excel — import/working view only (demoted 2026-07-24)

**The source of truth is now `records/<ID>.yaml`** — one validated YAML file per
dataset, reviewed via pull requests (see `records/README.md`). This Excel is kept
as an import/working view for people who prefer a spreadsheet, and as the CI
fallback until the Pages workflow installs PyYAML.

- Snapshot content: 68 records as of 2026-07-21 (unique literal Record IDs,
  Living landscape column normalized to controlled `CODE — Name` values —
  see `docs/REGISTRY_CHANGELOG_2026-07-21.md`).
- `scripts/excel_to_records.py` converts this workbook → `records/` (used for
  the one-time migration; reusable for bulk imports from focal points).
- **Until CI installs PyYAML** (one-line workflow edit, see README): after any
  edit under `records/`, keep this snapshot in step or CI will publish from the
  stale Excel. After that edit, this file no longer needs to track records/.
- `PER-PCL` (Pucallpa – Ucayali) is pending confirmation with the Peru team.
