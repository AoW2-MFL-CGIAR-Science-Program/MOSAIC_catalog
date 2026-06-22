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

**Input (one file):** `../catalog/MFL_Dataset_Registry.xlsx`, sheet `' Registry'` (the leading space is intentional). ~60 real records; the first data row is a placeholder/instructions row and is skipped.

**Output A — STAC catalog tree** (`stac/`): plain JSON, no pystac.
- `stac/catalog.json` (root)
- `stac/collections/<CODE>/collection.json` — one per living-landscape code (13)
- `stac/collections/<CODE>/items/<id>.json` — one per dataset (60)
- Uses `cgiar-cdh:*` and `mosaic:*` namespaces. Climate-themed items carry a `links[rel=related]` pointing to the CGIAR Climate Data Hub instead of re-describing it (connect, don't duplicate).

**Output B — frontend data contract:** `../MOSAIC_frontend/mfl-living-landscapes-frontend/frontend/data/datasets.json` — 60 flat records consumed by the existing catalogue pages.

## How it works

1. **Read** the registry, skip the placeholder row (`mosaic_pipeline/registry.py`).
2. **Transform** each row with rules R1–R9 — contact email, formats, license→SPDX, temporal split, etc. — emitting data-quality flags instead of crashing (`mosaic_pipeline/transform.py`).
3. **Resolve** controlled vocab: living-landscape crosswalk, country→M49/ISO3, approximate bbox (`mosaic_pipeline/vocab.py` + `spec/`).
4. **Emit** the STAC tree (`mosaic_pipeline/stac_build.py`) and `datasets.json` (`mosaic_pipeline/frontend_build.py`).
5. **Validate** the STAC tree structurally in pure Python (`mosaic_pipeline/validate.py`).

## Caveats and coverage

This is **functional, not perfect**. Honest numbers from the current registry:

- **living_landscape:** 58/60 mapped to a code; 2 malformed "Soil dataset" rows fall back to `GLB-UNSPEC`.
- **bbox:** 60/60 assigned but **APPROXIMATE** — country/landscape locator boxes, **not** precise coordinates (the registry has none). Flagged `mosaic:bbox_approximate: true`.
- **download_url:** 27/60 usable; the rest were "Internal" / "One drive" / server paths and are set to `null` (kept as an access note in STAC).
- **contact email:** 58/60 extracted.
- **formats:** the File name(s) column is empty, so `formats[]` falls back to `data_type`.
- **license / spatial_resolution:** non-SPDX licenses and messy resolution strings are kept verbatim and flagged.

**Provisional, pending confirmation:**
- Living-landscape codes and the bbox table are provisional until Lizeth's canonical landscape list is set.
- The CDH link URL is a **placeholder** pending the real CDH Collection URLs.
- The `mosaic:*` / `cgiar-cdh:*` extension schema JSONs are not yet hosted.

## Pointers

- Field rules and crosswalks: `spec/field_mapping.md`, `spec/vocab_reconciliation.md`, `spec/living_landscape_crosswalk.json`, `spec/bbox_lookup.json`.
- Governing spec: `MOSAIC_CDH_Interoperability_STAC_Assessment_202606.md`.
