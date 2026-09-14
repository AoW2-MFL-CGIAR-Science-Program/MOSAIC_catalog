# records/ — the MOSAIC dataset registry (source of truth)

Since **2026-07-24** the catalog's source of truth is this folder: **one YAML file
per dataset**, versioned in Git. The Excel workbook under `catalog/` is now only
an import/working view (see `catalog/SNAPSHOT_NOTE.md`).

Why this model: validated records (the build **fails** on invalid ones), stable
IDs that can never collide, a full audit trail per dataset (`git log
records/MFL-2026-001.yaml`), review via pull requests, and the same
metadata-in-Git pattern the CGIAR Climate Data Hub uses.

## Add a dataset

1. Pick the next free ID: `MFL-YYYY-NNN` (check the highest number in this folder).
2. Copy any existing record as a starting point (or use the template below),
   name the file exactly `<ID>.yaml`, and fill it in. Field-by-field docs:
   [`spec/record_schema.md`](../spec/record_schema.md).
3. Open a pull request (or, for non-Git contributors: submit the
   **"Register a new dataset"** issue form and a maintainer will do this step).
4. On merge to `main`, CI rebuilds and republishes the catalog automatically.

Validate locally before pushing:

```bash
python3 build_catalog.py
```

A build that prints `RECORD VALIDATION FAILED` lists exactly which file and
field to fix; nothing is published until it passes.

## Edit or retire a dataset

Edit the YAML file and open a PR. To retire a record, delete the file — its ID
stays reserved (never reuse IDs). Note the removal in the PR description.

## Rules

- Filename must equal the `id` field: `MFL-2026-001.yaml`.
- `living_landscape` holds a bare canonical code (`IND-CH`), or `NATIONAL`
  (country-wide dataset) or `GLOBAL` (global / cross-landscape).
- Controlled fields (`country`, `theme`, `data_type`, `access_level`,
  `processing_status`, `update_frequency`) must use a listed value or `null`.
- Unknown keys are rejected — if a fact has no field, propose a schema change
  instead of inventing keys.

## Minimal template

```yaml
# MOSAIC dataset record — schema: spec/record_schema.md (the build fails on invalid records)
id: MFL-2026-070
title: ""
description: null
country: ""            # required (since 2026-09-04) — one of the enum values
living_landscape: NATIONAL
theme: null
data_type: null
spatial_resolution: null
temporal_coverage: null
source: null
contact: ""            # required (since 2026-09-04) — "Name, email" in one string
access_level: null
license: null
processing_status: null
file_names: null
current_location: null
migration_status: null
server_path: null
date_registered: null
last_updated: null
update_frequency: null
download_url: null
file_size: null
```
