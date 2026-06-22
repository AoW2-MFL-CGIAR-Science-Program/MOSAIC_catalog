# MOSAIC field_mapping.md — Excel registry → frontend datasets.json AND → STAC

**Scope:** v1, functional. Two outputs from one registry row:
1. **Frontend** `frontend/data/datasets.json` (flat record, the live data contract).
2. **STAC** Collection JSON skeleton (`encoding: stac`), per the §3 crosswalk of `MOSAIC_CDH_Interoperability_STAC_Assessment_202606.md`.

**Source:** `MFL_Dataset_Registry.xlsx`, sheet `' Registry'` (LEADING SPACE in name). 23 columns. **Skip the first data row** (placeholder/instructions: values like "Auto-filled by formula", "Select from dropdown"). A row is a placeholder if Record ID is blank or any cell equals one of: `Auto-filled by formula`, `Select from dropdown`, or the instruction sentences.

**Checked (2026-06-22):** CDH `vocab/geography.json` (UN M49 confirmed) and `spec/mapping-stac.md` (contact roles = STAC provider roles; `file:size` required for primary asset; `cgiar-cdh:geography` array; SPDX preferred for license).

---

## 1. Excel column → frontend datasets.json key

| datasets.json key | Excel column | Rule |
|---|---|---|
| `id` | 1 Record ID | Keep `MFL-…` as-is (trim). If blank → generate `MFL-2026-<3-digit row index>` (see R6). Must be unique. |
| `title` | 2 Dataset title | Trim. If blank → `"Untitled dataset (<id>)"` and FLAG. |
| `country` | 3 Country | Map to canonical country enum (see vocab_reconciliation.md). Malformed `"Soil dataset"` → `null` + FLAG. |
| `living_landscape` | 5 Living landscape | Replace free text with CODE via `living_landscape_crosswalk.json` (trim+lowercase match). Unmatched → `GLB-UNSPEC` + FLAG. |
| `mfl_theme` | 4 MFL theme | Map to mfl_theme enum. `"Soil dataset"` → `null` + FLAG. |
| `data_type` | 6 Data type | Map to data_type enum {Raster,Vector,Tabular,Mixed}. `"Soil dataset"` → `null` + FLAG. |
| `spatial_resolution` | 7 Spatial resolution | Keep raw string for frontend display. See R5 (flag non-numeric). |
| `temporal_coverage` | 8 Temporal coverage | Keep raw string for frontend. (STAC splits it — R4.) |
| `source` | 9 Source / Centre | Trim. Map to centre enum where it matches (vocab_reconciliation.md). |
| `contact` | 10 Contact person | Extract **email** only (R1). If no email → `null`. |
| `access_level` | 11 Access level | Map to access_level enum {Open, CGIAR-internal, Restricted}. |
| `license` | 12 License | Map toward SPDX id; keep original as alias if non-SPDX (R3). |
| `readiness_status` | 13 Processing status | Map Raw/Processed/Validated → v1 readiness vocab (R7). |
| `formats` | 6 Data type + 14 File name(s) | Array; derive from file extensions, fallback to data_type (R2). |
| `description` | 18 Description / Notes | Trim. Empty string if blank. |
| `download_url` | 22 Primary source / Download URL | Clean (R8). Non-URL/"Internal"/"One drive" → `null`. |
| `metadata_url` | (generated) | Relative path to this dataset's STAC Item/Collection JSON (R9). |

Frontend keys NOT sourced from one column: `formats`, `metadata_url` (derived). `living_landscape` is the CODE, never the free text.

---

## 2. Excel column → STAC placement (`encoding: stac`, Collection-level)

Per §3 of the assessment. Use `cgiar-cdh:*` where the CDH defines it, `mosaic:*` for MOSAIC-only fields.

| Excel column | STAC placement | Namespace |
|---|---|---|
| 1 Record ID | `id` | core |
| 2 Dataset title | `title` | core |
| 3 Country | `cgiar-cdh:geography` (array of UN M49 ids) + drives `extent.spatial.bbox` | cgiar-cdh + core |
| 4 MFL theme | `themes[]` (Themes ext) + `mosaic:theme` | mosaic |
| 5 Living landscape | `mosaic:living_landscape` (CODE) | mosaic |
| 6 Data type | object type + asset `media_type`; selects Datacube vs Table ext | core |
| 7 Spatial resolution | `cgiar-cdh:spatial_resolution` (string for now; `{value,unit}` later) | cgiar-cdh |
| 8 Temporal coverage | `extent.temporal.interval` = `[[start, end]]` (R4) | core |
| 9 Source / Centre | `providers[]` (role producer/host) | core |
| 10 Contact person | `providers[]` + Contacts ext `contacts[]`; **≥1 `licensor`** | core + Contacts ext |
| 11 Access level | `mosaic:access_level` | mosaic |
| 12 License | `license` (SPDX) | core |
| 13 Processing status | `mosaic:processing_status` | mosaic |
| 14 File name(s) | `assets{}` keys / `data[].name` | core |
| 15 Current location | primary asset `href` | core |
| 16 Migration status | `mosaic:migration_status` | mosaic |
| 17 Server path | additional asset / Alternate Assets ext | core/ext |
| 18 Description / Notes | `description` (+ `cgiar-cdh:note` for structured leftovers) | core + cgiar-cdh |
| 19 Date registered | `created` | core |
| 20 Last updated | `updated` | core |
| 21 Update frequency | `mosaic:update_frequency` | mosaic |
| 22 Download URL | primary asset `href` / `links[rel=via]` | core |
| 23 File Size | `file:size` (File ext) | File ext |

**Not in registry, set by exporter:** `encoding: "stac"` (all spatial rows; a non-spatial document row → `"ogc-records"`), `mosaic_schema_version`, `extent.spatial.bbox` (from `bbox_lookup.json` until real geometries exist), `proj:code`/`proj:epsg` (CRS — absent in registry, leave null + FLAG).

**SKIP (CDH owns):** the climate block (`climate.*`) and CDH climate vocabularies (hazard, commodity). For climate layers, MOSAIC links to the CDH via `links[rel=related|via]` — do not redefine.

---

## 3. Transformation RULES (code these exactly)

### R1 — Contact email extraction (col 10 → `contact`)
Input is messy "Name - email" / "Name, email" / "Name (email)" / just a name / just an email.
1. Regex-find first email: `[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}`.
2. If found → `contact = <that email, lowercased, trimmed>`.
3. If none → `contact = null` and FLAG `missing_contact_email`.
4. (STAC only) the name portion = text before the first of ` - `, `,`, `(`; use for `contacts[].name`. Email → `contacts[].email`. Default `contacts[].role = "producer"`; ensure the Collection has **≥1 contact with role `licensor`** — if none, set the producer contact to `licensor` and FLAG `no_licensor_assigned`.

### R2 — formats[] derivation (cols 6 + 14 → `formats`)
1. From col 14 File name(s): extract all file extensions (regex `\.([A-Za-z0-9]{1,5})(?=[\s,;]|$)`), uppercase, dedupe. Map common ones: `tif/tiff→GeoTIFF`, `shp→Shapefile`, `gpkg→GeoPackage`, `csv→CSV`, `xlsx→XLSX`, `nc→NetCDF`, `geojson→GeoJSON`, `json→JSON`, `zarr→Zarr`, `parquet→Parquet`.
2. If no extensions found, fall back to col 6 Data type: `Raster→["GeoTIFF"]`, `Vector→["Shapefile"]`, `Tabular→["CSV"]`, `Mixed→["Mixed"]`.
3. Result is always a non-empty array; if everything fails → `["Unknown"]` + FLAG.

### R3 — License → SPDX (col 12 → `license`)
Map known values to SPDX ids; keep unknown CGIAR-specific strings verbatim and FLAG `non_spdx_license`.
| Registry value (case-insensitive contains) | `license` |
|---|---|
| CC BY 4.0 / CC-BY | `CC-BY-4.0` |
| CC BY-SA | `CC-BY-SA-4.0` |
| CC BY-NC | `CC-BY-NC-4.0` |
| CC0 / public domain | `CC0-1.0` |
| Open / open data (no specific license) | `other` + FLAG `vague_license` |
| (blank) | `null` + FLAG `missing_license` |
| anything else (e.g. "CGIAR internal use") | keep verbatim + FLAG `non_spdx_license` |

### R4 — Temporal coverage split (col 8 → STAC `extent.temporal.interval`)
Frontend keeps the raw string. For STAC only:
1. Find years/dates. Two found → `[["<start>-01-01T00:00:00Z","<end>-12-31T23:59:59Z"]]`.
2. One year found → `[["<y>-01-01T00:00:00Z","<y>-12-31T23:59:59Z"]]`.
3. None parseable (e.g. "Static", text) → `[[null, null]]` + FLAG `unparsed_temporal`.

### R5 — Spatial resolution (col 7 → `spatial_resolution`)
Keep the raw string for frontend. FLAG `non_numeric_resolution` when the value is not of form `<number><unit?>` (e.g. "Village level", "Admin - MFLLs Boundary", "5000", "25000" with no unit). These need `{value,unit}` normalization before STAC data-cube export — defer to Phase 2; do NOT block v1.

### R6 — id generation / normalization (col 1 → `id`)
1. Present → trim, keep verbatim (preserve `MFL-2026-000` style).
2. Blank → generate `MFL-2026-<NNN>` where NNN = zero-padded sequential index among real (non-placeholder) rows, starting after the highest existing `MFL-2026-NNN` to avoid collision.
3. Enforce uniqueness across the run; on duplicate append `-2`, `-3` and FLAG `duplicate_id`.

### R7 — readiness_status map (col 13 → `readiness_status`)  ** DECISION **
**v1 readiness_status vocab = the registry's own three values: `["Raw","Processed","Validated"]`.**
Rationale: the registry IS the single source of truth; remapping onto the 5-value frontend enum (`Registered only / Under review / Accepted / Validated / Analytics-ready`) invents distinctions the data does not carry and risks misclassification. Simplest correct answer wins. **Update the frontend `metadata_schema.json` readiness_status enum to `["Raw","Processed","Validated"]`** (see vocab_reconciliation.md).
Map:
| col 13 value | `readiness_status` |
|---|---|
| Raw | `Raw` |
| Processed | `Processed` |
| Validated | `Validated` |
| (blank / other) | `Raw` + FLAG `missing_readiness` |

### R8 — download_url cleaning (col 22 → `download_url`)
1. Trim. Take first line if multi-line.
2. Valid only if it starts with `http://` or `https://` (or `ftp://`).
3. Reject (→ `null`) free text: `Internal`, `One drive`, `OneDrive`, `On request`, `N/A`, `-`, `TBD`, server paths, anything without a scheme. FLAG `non_url_download` so it can later become an access note rather than an `href`.

### R9 — metadata_url generation (→ `metadata_url`)
Relative path convention pointing to this dataset's STAC JSON:
```
metadata_url = "stac/collections/" + <id> + "/collection.json"
```
- `<id>` is the cleaned/normalized id from R6, URL-safe (replace any char outside `[A-Za-z0-9._-]` with `-`).
- This file need not exist yet in v1 (STAC export is Phase 2); the path is the stable contract the exporter will honor. Frontend may treat a 404 gracefully.
- One Collection per dataset (registry is collection-level per §3.4). Item-level deferred.

---

## 4. Data-quality FLAGS the engineer must emit (for a side report, not to block v1)
`missing_contact_email`, `no_licensor_assigned`, `non_spdx_license`, `vague_license`, `missing_license`, `unparsed_temporal`, `non_numeric_resolution`, `duplicate_id`, `missing_readiness`, `non_url_download`, `malformed_row` (the "Soil dataset" record), `unmatched_living_landscape`, `missing_crs`.

Emit as `flags: []` per record in an export log. v1 ships even with flags present.
