# MOSAIC catalog pipeline

Turns the **MFL Dataset Registry** (one Excel file, the single source of truth) into two machine-readable artifacts: a static **STAC catalog** and the frontend **`datasets.json`**. Part of MOSAIC, the geospatial coordination network for the CGIAR MFL Science Programme (AoW2). MOSAIC connects metadata across CGIAR centres and external services — it does not re-host data ("connect, don't duplicate").

## Quickstart

```bash
cd "MOSAIC_development/MOSAIC_catalog"
python3 build_catalog.py
```

Prerequisites: **Python 3** and **openpyxl** (pandas and Pillow are also available). No Node/npm — validation is pure Python, by design (the npm registry is blocked here and the CDH npm CI is intentionally not used).

The run is **idempotent**: it wipes and rebuilds `stac/` and overwrites `datasets.json` every time. It prints a coverage report and exits non-zero if STAC validation fails.

## Inputs and outputs

**Input — source of truth (since 2026-07-24):** `records/<ID>.yaml` — one validated
YAML file per dataset (68 records), reviewed via PRs. See `records/README.md` to
add or edit datasets and `spec/record_schema.md` for the field docs. Invalid
records abort the build. The Excel workbook (`catalog/MFL_Dataset_Registry.xlsx`)
is retained as an import/working view only; `--from-excel` forces it as source
(the two paths are acceptance-tested byte-identical).

> **CI note:** the Pages workflow still runs `pip install openpyxl` only. Until
> `pyyaml` is added to that line (one-line edit in
> `.github/workflows/build-and-pages.yml`, via the GitHub web UI — the local
> token cannot push workflow changes), CI falls back to the Excel snapshot with
> a loud warning, so the snapshot must be kept in sync after record edits
> (`python3 scripts/excel_to_records.py` works Excel→records; regenerating the
> snapshot the other way is manual until then).

**Output A — STAC catalog tree** (`stac/`): plain JSON, no pystac.
- `stac/catalog.json` (root)
- `stac/collections/<CODE>/collection.json` — one per canonical living landscape (11, all delineated — created even when empty) + `GLB` for global datasets (12 total)
- `stac/collections/<CODE>/items/<id>.json` — one per dataset (68)
- `stac/boundaries/<CODE>.geojson` — the canonical landscape delineations (simplified, EPSG:4326), copied from the committed `boundaries/` folder; each collection exposes its boundary as a `boundary` asset
- Uses `cgiar-cdh:*` and `mosaic:*` namespaces. Climate-themed items carry a `links[rel=related]` pointing to the CGIAR Climate Data Hub instead of re-describing it (connect, don't duplicate).

**Output B — frontend data contract:** `datasets.json` — 68 flat records consumed by the catalogue pages (synced into the frontend repo with `--sync-frontend`).

**Boundaries build (local only):** `python3 scripts/build_boundaries.py` regenerates `boundaries/` and the real bboxes in `spec/bbox_lookup.json` from the delineation shapefiles in `../MOSAIC_LLV_delim` (needs geopandas; CI never runs this — it just copies the committed GeoJSONs).

## How it works

1. **Read** the registry, skip the placeholder row (`mosaic_pipeline/registry.py`).
2. **Transform** each row with rules R1–R9 — contact email, formats, license→SPDX, temporal split, etc. — emitting data-quality flags instead of crashing (`mosaic_pipeline/transform.py`).
3. **Resolve** controlled vocab: living-landscape crosswalk, country→M49/ISO3, approximate bbox (`mosaic_pipeline/vocab.py` + `spec/`).
4. **Emit** the STAC tree (`mosaic_pipeline/stac_build.py`) and `datasets.json` (`mosaic_pipeline/frontend_build.py`).
5. **Validate** the STAC tree structurally in pure Python (`mosaic_pipeline/validate.py`).

## Caveats and coverage

This is **functional, not perfect**. Honest numbers from the current registry (68 records, 2026-07-21):

- **living_landscape:** 66/68 mapped to a canonical landscape; 2 global datasets sit in `GLB`. Coverage split: 57 landscape, 9 national (`mosaic:coverage: national`, assigned to the country's landscape collection), 2 global.
- **bbox:** 68/68 assigned. Landscape-coverage items use the **real delineation-derived bbox** (still flagged `mosaic:bbox_approximate: true` because the dataset's *own* extent is unrecorded — the landscape box is a proxy). National/global items use locator boxes. **Collection** extents are delineation-derived and flagged `false`.
- **download_url:** 32/68 usable; the rest were "Internal" / "One drive" / server paths and are set to `null` (kept as an access note in STAC).
- **contact email:** 66/68 extracted.
- **formats:** the File name(s) column is empty, so `formats[]` falls back to `data_type`.
- **license / spatial_resolution:** non-SPDX licenses and messy resolution strings are kept verbatim and flagged.

**Canonical vs. pending:**
- The landscape list (11 codes + `NATIONAL`/`GLOBAL` coverage values) is **canonical**, approved 2026-07-21 — see `spec/living_landscape_crosswalk.json` and `docs/REGISTRY_CHANGELOG_2026-07-21.md`.
- **`PER-PCL` (Pucallpa – Ucayali) is pending confirmation** with the Peru team (the older reference map said Apurímac; the delivered shapefile is Pucallpa/Ucayali). Flagged `mosaic:pending_confirmation: true`.
- National-coverage **Kenya** datasets sit in `KEN-LVB` (primary) with a `related` link to `KEN-LEI`.
- The CDH link URL is a **placeholder** pending the real CDH Collection URLs.
- The `mosaic:*` / `cgiar-cdh:*` extension schema JSONs are not yet hosted.

## Pointers

- **Registering datasets (focal-point guide): `docs/HOW_TO_REGISTER_DATASETS.md`** — the form, the PR path, and bulk import.

- Field rules and crosswalks: `spec/field_mapping.md`, `spec/vocab_reconciliation.md`, `spec/living_landscape_crosswalk.json`, `spec/bbox_lookup.json`.
- Governing spec: `MOSAIC_CDH_Interoperability_STAC_Assessment_202606.md`.
