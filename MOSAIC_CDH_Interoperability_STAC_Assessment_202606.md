# MOSAIC ↔ CGIAR Climate Data Hub — STAC & Interoperability Assessment

**Programme:** CGIAR MFL Science Programme — AoW2 (Landscape Optimization & Inclusive Planning)
**Initiative:** MOSAIC (Multifunctional Open Spatial Analysis & Integration Collaborative)
**Prepared by:** Lizeth Llanos, Technical Coordinator — MOSAIC
**Date:** June 2026
**Status:** Internal technical assessment for decision

---

## 1. Executive summary

Brayden's team at the CGIAR Climate Data Hub (CDH) has built a lightweight, AI- and human-readable **metadata standard** for climate datasets, and — most importantly for us — a clear, documented mapping from that standard to **STAC** (SpatioTemporal Asset Catalog), the de-facto open standard for describing geospatial data. STAC is the part of their work that is most advanced and most relevant to MOSAIC. Their CDH framework is still an explicit DRAFT (version v0.0.1, breaking changes expected), but the architecture is sound and the alignment opportunity is real and timely: it is far cheaper to align now, while both hubs are early, than to retrofit later.

**What the CDH built (in plain terms).** A small set of required metadata fields ("enough for someone to find, understand, cite, and access a dataset without opening the files"), a controlled vocabulary, an authoring template in YAML, and a rulebook for turning each record into a standard STAC catalog entry. They route each record through one of two serialization profiles via an `encoding` field (`stac` for spatial/temporal data, `ogc-records` for the rest), reuse a dozen community STAC extensions, and add a single hub-specific extension (`cgiar-cdh`) only for fields the standards do not already cover. Validation and continuous integration run on a Node/npm toolchain.

**What MOSAIC should adopt.** Three things, in priority order:
1. **STAC as MOSAIC's target metadata standard** for spatial datasets, with the same "native-fields-first" placement discipline the CDH uses. This is the single most important interoperability decision.
2. **The CDH's core required-field set and authoring philosophy** — adopt the shared concepts (`id`, `title`, `description`, `license`, `contact`/roles, `citation`, spatial/temporal extent, provenance) so our records and theirs describe the world the same way.
3. **Shared controlled vocabularies for the fields that must match** — geography (UN M49), license (SPDX), contact roles, and a thematic vocabulary aligned to (not merged with) the CDH's `domain`.

**What MOSAIC should adapt or skip.** MOSAIC is broader than climate: it spans the **13 MFL themes**, not one domain. So we adapt the CDH's single-domain model into a 13-theme thematic vocabulary, and we **skip the climate-specific block** (`climate.*`: mip_era, scenarios, GCM models, bias adjustment, downscaling) and the climate-only `cgiar-cdh` fields — those stay the CDH's responsibility. This is "connect, don't duplicate" applied at the schema level: for climate layers, MOSAIC links to the CDH rather than re-describing them.

**The interoperability path.** MOSAIC remains a coordination network and metadata system, not a repository. The two hubs interoperate by (a) describing datasets with the **same STAC core and the same shared vocabularies**, so a record can be read by either side; and (b) **cross-linking their STAC catalogs** using standard STAC link relations (`child`, `related`, `via`) so MOSAIC can point at a CDH dataset as the source of truth instead of copying it. We do not need a single shared catalog; we need two catalogs that speak the same language and link to each other.

**The honest near-term constraint.** A real STAC catalog (served JSON, validated, browsable) is a later-2026/2027 build. The CDH's validation/CI toolchain is npm-based, and npm is blocked in our environment; their schemas can be *read and mirrored*, but their tooling cannot be *run* here as-is. The good news is that the catalog is no longer a blank template: it now holds **60 real dataset records** spanning **~14 living landscapes** across the programme countries. So the recommended 2026 move is concrete, not hypothetical — make the registry **STAC-aligned by design** (rename and add a handful of fields, adopt the shared vocabularies) and run a **STAC-export pilot against the real records** to prove the mechanical path end-to-end. We collect the *right* fields in the *right* shape, and we test the export on content we already have.

---

## 2. What the CDH has built — focus on STAC

### 2.1 A standard, not a database
The CDH `metadata` repository is a **specification + schemas + vocabulary + authoring templates**, MIT-licensed. It defines a metadata input record (authored in YAML) and the rules for encoding it. There is one semantic version across the whole framework (standard + schemas + vocab + STAC extension), carried in each record's `cdh_schema_version` field, currently `v0.0.1`. The README states plainly that it is a draft and breaking changes are expected.

This matters for MOSAIC: the CDH is itself a metadata/coordination layer, the same category of thing MOSAIC is. We are aligning two metadata standards, not plugging into a finished product.

### 2.2 The `encoding` routing idea
Every record declares an `encoding`: either `stac` or `ogc-records`. This single field decides which serialization profile (and which mapping document) applies.
- `encoding: stac` → use the STAC mapping. Chosen when the resource has meaningful **spatial / temporal / asset-level / variable-level / data-cube** discovery needs: rasters, COGs, Zarr, NetCDF, GeoParquet, gridded climate, spatial vector, spatial/temporal tabular, geospatial APIs.
- `encoding: ogc-records` → use the OGC API – Records mapping. Chosen for non-spatial resources (documents, tools, tabular without spatial/temporal aspect).

This is an elegant, reusable pattern: one authoring template, two standards-compliant outputs, decided per record. MOSAIC should adopt the concept directly — most MOSAIC datasets are spatial and route to STAC; non-spatial items (a methods document, a decision-support report) route to OGC API – Records.

### 2.3 STAC extensions the CDH reuses
The CDH's design principle is **native-fields-first**: put each fact in the most standard place available, and only invent a hub-specific field as a last resort. Placement priority is:

1. a **core STAC** field;
2. a **community STAC extension** field;
3. an approved **`cgiar-cdh:*`** field;
4. a **sidecar metadata asset** linked `rel=describedby`;
5. free-text `description` / `cgiar-cdh:note`.

Free text must never be the only home for a searchable, structured fact.

Extensions in use:

| STAC extension | Carries |
|---|---|
| **Scientific** | DOI, citation, related publications |
| **Datacube** | dimensions, variables, units, nodata for cubes / Zarr / NetCDF / any array data (a 2D raster is a valid cube) |
| **Raster** | per-band physical metadata |
| **Table** | columns, row count, primary geometry (tabular) |
| **Classification** | class values, labels, bitfields |
| **Projection** | CRS / EPSG |
| **Processing** | processing datetime, lineage, software |
| **Contacts** | people / organizations (beyond STAC providers) |
| **Version** | version, predecessor / successor |
| **File** | file size |
| **Alternate Assets** | mirrors / alternate access locations |
| **Themes** | controlled-vocabulary thematic classification (encoder output) |
| **cgiar-cdh** (custom) | hub-specific approved fields not covered above |

### 2.4 The `cgiar-cdh` extension
A single custom STAC extension holds everything the community standards do not cover: `cgiar-cdh:domain`, `cgiar-cdh:geography`, `cgiar-cdh:resource_type`, `cgiar-cdh:spatial_resolution` / `:temporal_resolution`, `:note`, `:funding`, `:use_cases`, `:not_recommended_for`, and the climate block (`mip_era`, `scenarios`, `models`, `hazards`, `baseline`, `bias_adjustment`, `downscaling`). Commodities and climate hazards are also expanded into the **Themes** extension via JSON lookups. Critically, **every `cgiar-cdh:*` field must be defined in the CDH STAC Extension schema** — undefined fields fail validation.

The lesson for MOSAIC: a custom extension is normal and expected, but it should be *small* and *schema-defined*. MOSAIC will need its own minimal `mosaic:*` namespace for the few MFL-specific facts (e.g. MFL theme, landscape name, migration status) that have no standard home.

### 2.5 Vocabulary, validation, authoring
- **Vocabularies** (`vocab/`): `domain.json`, `resource_type.json`, `commodity.json`, `hazard.json` (each validated against `vocabulary.schema.json`), plus `geography.json` (UN M49 ids). These are machine-readable JSON, not free text.
- **Validation / CI** (npm-based): `npm test` runs markdown lint + schema/vocab/YAML validation; `npm run check`; `npm run gen-schemas` regenerates schema fragments after vocab edits. Bare ESM imports on Node.js. Pre-commit hooks. The whole workflow is adapted from the official STAC-extensions template project.
- **Authoring workflow.** Minimum record fields: `id`, `title`, `description`, `resource_type`, `encoding`, `cdh.domain`, `keywords`, `license`, `contact`, `citation`, `created`, `updated`, `data`. Optional blocks (`spatial`, `temporal`, `variables`, `dimensions`, `classes`, `processing`, `climate`) are added only when they apply.
- **Division of labour** (directly relevant to MOSAIC's "coordinate, don't produce" role): the **contributor** supplies curatorial judgement (title, description, license, domain, variable meanings/units, caveats, publication-eligibility); the **CDH review** fills technical metadata that can be extracted from the files (timestamps, media types, file sizes, CRS, bounding boxes). This split is a good model for MOSAIC's focal-point workflow.

---

## 3. Field-by-field crosswalk

Anchor = MOSAIC's current Excel registry (23 columns, populated with 60 real records). For each MOSAIC column we give the closest **CDH field** and the **STAC placement** it would land in (`encoding: stac`). The final columns flag the action.

Legend — **Action:** Keep = already aligned; Rename = same concept, align label/values; Split = one MOSAIC column feeds several standard fields; Add-value = constrain to a shared vocabulary; OK-as-note = no clean standard home, stays MOSAIC-local.

### 3.1 MOSAIC columns → CDH → STAC

| # | MOSAIC registry column | CDH field | STAC placement (`encoding: stac`) | Match | Action |
|---|---|---|---|---|---|
| 1 | Record ID | `id` | `id` (Collection) | Exact concept | Keep (keep `MFL-…` scheme; ensure globally unique) |
| 2 | Dataset title | `title` | `title` | Exact | Keep |
| 3 | Country | `spatial.geography[]` | `cgiar-cdh:geography` (+ drives bbox) | Concept match, **vocab differs** | Rename → `geography`; **Add-value**: adopt UN M49 ids from shared `geography.json` (e.g. "Côte d'Ivoire") |
| 4 | MFL theme | (CDH uses `cdh.domain` — single climate domain) | Themes ext `themes[]` + `mosaic:theme` | **MOSAIC-broader gap** | Keep MFL 13-theme list; expose as a MOSAIC thematic vocabulary aligned *alongside* CDH `domain`, not merged |
| 5 | Living landscape | none (MOSAIC-specific concept) | No native STAC/CDH home → `mosaic:living_landscape` | **Gap (MOSAIC-specific)** | Keep as `mosaic:*` custom field; **control the vocabulary** against the official MFL living-landscape list (currently free text and messy — ~14 distinct values across 60 records; directly supports the 2026 landscape-delineation objective) |
| 6 | Data type (Raster/Vector/Tabular/Mixed/Netcdf) | `resource_type` (dataset) + encoder tabular-or-not decision | Object type (Collection) + asset `media_type`; drives Datacube vs Table ext | Partial | Rename/Split: keep as MOSAIC hint; real type is inferred at encoding from media type |
| 7 | Spatial resolution | `spatial.resolution[]` | `cube:dimensions[].step` + `cgiar-cdh:spatial_resolution` | Concept match, **less structured in MOSAIC** | Rename → `spatial_resolution`; later structure (value+unit) |
| 8 | Temporal coverage | `temporal.start_date` / `end_date` | `extent.temporal.interval` (+ `cgiar-cdh:temporal_resolution`) | Concept match, **MOSAIC stores a string** | Split into start/end dates; keep human range in description |
| 9 | Source / Centre | `contact[role=producer/host]` + `processing[].derived_from` | `providers[]` + Contacts ext | Concept match | Map to provider roles (see below) |
| 10 | Contact person (name + email) | `contact[]` (name, email, role, organization) | `providers[]` + Contacts ext `contacts[]`; ≥1 `licensor` | Concept match, **MOSAIC lacks role** | Rename/Split; **Add**: contact role vocab (licensor/producer/processor/host) |
| 11 | Access level (Open / CGIAR-internal / Restricted) | (no direct field; implied by `license` + access) | No native STAC field → `mosaic:access_level` | **Gap (MOSAIC-specific)** | Keep as `mosaic:access_level` (small custom field) |
| 12 | License | `license` | `license` (SPDX preferred) | Concept match, **vocab differs** | Rename values toward **SPDX**; keep CGIAR-specific licenses as documented aliases |
| 13 | Processing status (Raw/Processed/Validated) | `processing[]` lineage; (`resource_type`) | Processing ext `processing:lineage` | Partial | Keep as `mosaic:processing_status`; richer lineage optional later |
| 14 | File name(s) | `data[].name` | `assets{}` key / `data[].name` | Concept match | Keep; feeds asset definitions |
| 15 | Current location | `data[].locations[].url` | asset `href` (canonical = `locations[0].url`) | Concept match | Rename → asset location URL |
| 16 | Migration status (Registered only / Migrated) | — | No native field → `mosaic:migration_status` | **Gap (MOSAIC-specific)** | Keep as small custom field (operational, MOSAIC-only) |
| 17 | Server path | `data[].locations[].url` (S3/HTTPS) + Alternate Assets | additional `assets` / Alternate Assets ext | Concept match | Rename → second asset location (`title: S3` / `HTTPS`) |
| 18 | Description / Notes | `description` (+ `note`, `cdh.not_recommended_for`) | `description` + `cgiar-cdh:note` | Concept match | Keep; move *structured* facts out of prose into fields |
| 19 | Date registered (auto) | `created` | `created` (Collection) | Exact | Keep |
| 20 | Last updated | `updated` | `updated` | Exact | Keep |
| 21 | Update frequency (Annual/Seasonal/Monthly/On-demand/Static/Unknown) | (`temporal.resolution` is different) | No native field → `mosaic:update_frequency` | **Gap (MOSAIC-specific)** | Keep as small custom field |
| 22 | Primary source / Download URL | `data[].locations[].url` | asset `href` / `links[rel=via|canonical]` | Concept match (partially closes the old "no download URL" gap) | Rename → asset href; **needs cleanup** (56/60 filled, but values mix real URLs with free text like "Internal") |
| 23 | File Size (bytes) | `data[].file_size` | File ext `file:size` | Exact concept | Keep → `file:size` (closes the structural file-size gap; column exists but only 1/60 populated → an adoption gap, not a schema gap) |

### 3.2 CDH / STAC fields MOSAIC currently lacks (adoption gaps)

| Missing in MOSAIC | CDH field | STAC placement | Why MOSAIC needs it |
|---|---|---|---|
| **Encoding selector** | `encoding` | routes whole record | Decides STAC vs OGC-Records; foundational for any export |
| **Schema version** | `cdh_schema_version` | n/a (provenance of the record itself) | Lets us track which standard version a record follows; add `mosaic_schema_version` |
| **Spatial extent (bbox)** | `spatial.bbox` | `extent.spatial.bbox` | Core to spatial discovery; **completely absent** today |
| **CRS** | `spatial.crs` | Projection `proj:code` / `proj:epsg` | Required to use any geospatial layer correctly |
| **Citation** | `citation` (required) | `sci:citation` | Required for credit/reuse; absent today |
| **DOI** | `doi` | `sci:doi` + `links[rel=cite-as]` | Stable identifier when available |
| **Contact role** | `contact[].role` | provider roles; ≥1 `licensor` | Distinguishes who licenses vs produces vs hosts |
| **Media type** | `data[].media_type` | asset `type` | Needed to interpret/serve the file |
| **Provenance / derived-from** | `processing[]`, `derived_from` | Processing ext + `links[rel=derived_from]` | Lineage; supports "connect, don't duplicate" by pointing at sources |
| **Keywords** | `keywords` | `keywords` / Themes ext | Free + controlled search terms |

**Now CLOSED structurally (columns added; remaining work is population/cleanup, not schema):**
- **File size** — CLOSED. Col 23 "File Size" exists and maps to File ext `file:size`. Remaining issue is an **adoption gap**: only 1/60 records populated.
- **Download URL** — partially CLOSED by col 22 "Primary source / Download URL" (asset `href` / `links[rel=via|canonical]`). 56/60 filled, but values need **cleanup** (mix of real URLs and free text like "Internal").

### 3.3 MOSAIC fields with no clean standard home (keep MOSAIC-local)

These are operational fields specific to MOSAIC's interim workflow. They have no native STAC slot and should live under a small `mosaic:*` extension (mirroring how the CDH keeps a small `cgiar-cdh:*` namespace). They are **mappable, not identical** — they need not match the CDH.

- **Access level** (Open / CGIAR-internal / Restricted) → `mosaic:access_level`
- **Living landscape** → `mosaic:living_landscape`; should become a **controlled vocabulary** tied to the official MFL living-landscape list (currently free text and messy)
- **Migration status** (Registered only / Migrated to Alliance server) → `mosaic:migration_status`
- **Update frequency** (Annual / Seasonal / Monthly / On-demand / Static / Unknown) → `mosaic:update_frequency`
- **Processing status** (Raw / Processed / Validated) → `mosaic:processing_status` (complements, does not replace, the Processing extension)

### 3.4 The big structural gap
The CDH model is **collection-level by design** (its YAML records describe whole datasets, exactly like a MOSAIC registry row). That is excellent news: a MOSAIC row maps cleanly to a **STAC Collection**, with one or more **Assets** for the file(s). The principal gaps are not structural — they are **missing facts**: bbox, CRS, citation, contact roles, media type, and the `encoding` selector. Those are the fields the crosswalk says to add. Note that **file size and download URL now have columns** (cols 23 and 22): the remaining issue there is population and cleanup, not schema.

---

## 4. Recommendations — adopt / adapt / skip

Each recommendation is tied to MOSAIC's principle (**connect, don't duplicate**), to the fact that **MOSAIC spans 13 MFL themes** (not one climate domain), and to Lizeth's **coordinate-not-produce** role.

### 4.1 ADOPT (align tightly — these should match the CDH)

| # | Adopt | Rationale |
|---|---|---|
| A1 | **STAC as MOSAIC's target standard** for spatial datasets (Collection-level), with the native-fields-first placement discipline | The single decision that makes interoperability possible. STAC is the open standard both hubs and the wider community already use. |
| A2 | **The CDH core required-field set & authoring philosophy** — "enough to find, understand, cite, access without opening the files"; contributor-vs-review division of labour | Fits MOSAIC's coordination role exactly: focal points supply curatorial judgement; technical fields (bbox, CRS, size) can be filled at review/export. |
| A3 | **Shared controlled vocabularies for must-match fields**: geography (UN M49), license (SPDX), contact roles | These are the fields that have to be *identical* for a record to be read by either hub. Aligning vocab is cheap now, costly later. |
| A4 | **The `encoding` routing concept** (`stac` for spatial, `ogc-records` for non-spatial) | One authoring template → standards-compliant output; cleanly handles MOSAIC's non-spatial items (documents, decision-support outputs) too. |
| A5 | **A small, schema-defined custom extension** (`mosaic:*`) for MFL-specific operational fields | Mirrors the CDH's disciplined `cgiar-cdh:*` approach: custom fields are allowed, but few and validated. |
| A6 | **Living landscape as `mosaic:living_landscape`, AND control its vocabulary** against the official MFL living-landscape list | The column already exists and is filled for 59/60 records (~14 distinct values, currently free text and messy). Adopting it as a `mosaic:*` field and constraining its values directly serves the **2026 landscape-delineation objective** — an actionable adopt-and-control item, not a hypothetical one. |

### 4.2 ADAPT (same idea, MOSAIC-broader shape)

| # | Adapt | Rationale |
|---|---|---|
| B1 | **Domain → 13 MFL themes.** Keep MOSAIC's MFL theme vocabulary; align it *alongside* the CDH `domain` (so climate maps cleanly), do not collapse into it. | MOSAIC is multi-theme by definition. The CDH's single `domain: [climate]` is a special case of MOSAIC's wider thematic axis. |
| B2 | **Excel registry → STAC-aligned interim registry.** Re-label columns to standard field names, add the **still-missing** facts (bbox, CRS, citation, roles, media type, encoding), adopt shared vocabularies. *Download URL and File Size already have columns (cols 22, 23) — those are data-hygiene items (populate/clean), not new fields to add (see §6).* | Lets MOSAIC keep collecting *now* in the tool focal points already have, while guaranteeing a clean export to STAC JSON later. No premature platform build. |
| B3 | **Resource type.** Adopt the CDH set (`dataset`/`document`/`tool`/`ai-skill`) as a MOSAIC field; keep MOSAIC's Data type (Raster/Vector/…) as the encoder's tabular-or-not hint. | Two complementary axes; both useful, neither redundant. |

### 4.3 SKIP (CDH-specific — let the CDH stay the source of truth)

| # | Skip | Rationale |
|---|---|---|
| C1 | **The climate block** (`climate.*`: mip_era, scenarios, GCM models, hazards, baseline, bias_adjustment, downscaling) | Pure climate-modelling metadata. MOSAIC does not produce climate projections; for climate layers MOSAIC **links to the CDH**. Re-describing them here would duplicate the CDH — the exact thing our principle forbids. |
| C2 | **Climate-only vocabularies** (`hazard.json`, `commodity.json` as CDH-owned) | These are the CDH's domain. MOSAIC may *reference* them where a record overlaps, but should not maintain its own copies. |
| C3 | **Running the CDH npm validation/CI toolchain in MOSAIC's environment** | npm is blocked here. MOSAIC mirrors the CDH's *schemas* (read-only JSON) for alignment but builds its own lightweight, Python-based checks (see §6). |
| C4 | **Building a full STAC server now** | Not a 2026 objective. MOSAIC's 2026 job is gap analysis, minimum spatial package, landscape delineation, and use cases — all servable from the interim registry. The catalog is a 2027 build. |

---

## 5. Interoperability mechanism — how the two hubs talk

MOSAIC stays a **coordination network and metadata system**: it links to the CDH, it does not absorb it. Concretely, four mechanisms, with an explicit statement of **what must be identical** vs. **what need only be mappable**.

### 5.1 Aligned metadata schema (mostly identical core, MOSAIC-broader edges)
- **Must be identical:** the STAC *core* (`id`, `title`, `description`, `license`, `created`, `updated`, extents), and the shared vocabularies (geography UN M49, license SPDX, contact roles). If these differ, records cannot be read across hubs.
- **Must be mappable, not identical:** the thematic axis (MOSAIC's 13 MFL themes ↔ CDH `domain`) and each hub's custom namespace (`mosaic:*` ↔ `cgiar-cdh:*`). A documented crosswalk (this report's §3 is the seed) is enough; the values themselves can differ.

### 5.2 STAC catalog cross-linking (the heart of "connect, don't duplicate")
Once both hubs publish STAC, they link rather than copy, using standard STAC **link relations**:
- A MOSAIC landscape catalog includes a CDH climate dataset by reference via `links[rel=child]` (if MOSAIC nests it) or, preferably, `links[rel=related]` / `links[rel=via]` pointing at the CDH Collection URL. The CDH remains the **source of truth**; MOSAIC holds only a pointer + minimal discovery metadata.
- Cross-hub provenance uses `links[rel=derived_from]` and `links[rel=cite-as]` so a MOSAIC-derived product can point back to its CDH climate inputs.
- Result: a researcher browsing MOSAIC by landscape sees climate layers in context, but clicks through to the CDH for the authoritative copy. No data and no full metadata are duplicated.

### 5.3 Shared controlled vocabularies
- **Identical, shared:** `geography.json` (UN M49) and license (SPDX) — adopt the CDH's files directly or maintain a byte-identical mirror.
- **Aligned via lookup:** MOSAIC's MFL-theme vocabulary carries a documented mapping to CDH `domain` (and, where relevant, to the STAC **Themes** extension `scheme`), so a climate record tagged in either hub resolves consistently.

### 5.4 The `encoding` routing convention
Both hubs adopt the same `encoding: stac | ogc-records` switch with the same routing rule (spatial/temporal → STAC; otherwise → OGC API – Records). This guarantees that a record authored in one hub serializes to the same standard in the other — the precondition for any cross-read.

### 5.5 Governance & versioning alignment (coordinate with Brayden)
- The CDH uses **one semantic version across standard + schemas + vocab + extension**, stamped in each record (`cdh_schema_version`). MOSAIC should mirror this discipline with its own `mosaic_schema_version`, and — critically — **agree a shared-vocabulary version line with the CDH** so that when UN M49 / SPDX / contact-role sets change, both hubs move together. This is the one piece of true joint governance required.
- Everything else (each hub's themes, each hub's custom extension, release cadence) can version independently as long as the crosswalk is maintained.

**Summary of the identical-vs-mappable split:**

| Layer | Identical (must match) | Mappable (crosswalk is enough) |
|---|---|---|
| STAC core fields | ✓ | |
| Geography (UN M49), License (SPDX), Contact roles | ✓ | |
| `encoding` routing convention | ✓ | |
| Shared-vocab version line | ✓ (joint governance) | |
| Thematic axis (MFL themes ↔ domain) | | ✓ |
| Custom namespaces (`mosaic:*` ↔ `cgiar-cdh:*`) | | ✓ |
| Operational fields (access, migration, update freq) | | ✓ (MOSAIC-local) |

---

## 6. Implementation roadmap for 2026

Phased and concrete. Items needing **Brayden/CDH coordination** are flagged **[COORD]**. The guiding split: **what MOSAIC can do now with the Excel interim registry** vs. **what needs a real STAC catalog later (2027)**.

### Technical feasibility notes (environment realities)
- **npm is blocked.** The CDH's `npm test` / `gen-schemas` toolchain cannot run in MOSAIC's environment. We can *read and mirror* their JSON schemas and vocab files (plain JSON), but not execute their Node CI. → MOSAIC builds lightweight **Python** validation (openpyxl/pandas/`json` are available; `jsonschema` for schema checks) instead.
- **`pystac` is not installed** and may not be installable here. This is fine: a STAC Collection is plain JSON, so MOSAIC can generate STAC-aligned JSON with the Python standard-library `json` module. `pystac` would be a convenience, not a requirement.
- **The Excel registry can be mechanically exported.** Because both the registry and the CDH model are *collection-level*, each registry row maps to one STAC Collection JSON skeleton. A ~100-line Python script (openpyxl → dict → json) is sufficient for a first export, once the missing fields exist.

### Phase 1 — Now (Q3 2026): make the interim registry STAC-aligned *by design*
Excel-based; no platform build. Delivers immediate value to the 2026 gap-analysis and minimum-spatial-package objectives.
1. **Re-label registry columns** to standard field names and **add the still-missing facts** as new columns: `encoding`, `bbox` (xmin/ymin/xmax/ymax), `crs`, `citation`, `doi`, `contact_role`, `media_type`, `keywords`, `mosaic_schema_version`. (From §3.2.) *Note: File Size and Download URL already exist as cols 23 and 22 — they are not added here; cleaning/populating them is a hygiene task in Phase 2.*
2. **Adopt shared vocabularies** as dropdowns: geography → UN M49 ids; license → SPDX values (keep CGIAR licenses as documented aliases); contact roles → licensor/producer/processor/host. **[COORD]** confirm exact files/values with Brayden so they are byte-aligned.
3. **Keep MOSAIC-local fields** (access level, migration status, update frequency, processing status) as a clearly labelled "MOSAIC operational" block → future `mosaic:*`.
4. **Adopt the contributor-vs-review division of labour** in the focal-point workflow: focal points fill curatorial fields; bbox/CRS/size/media-type can be completed at MOSAIC review/export. This matches Lizeth's coordinate-not-produce mandate.
5. **Write the minimum-field rule** into the registry Instructions sheet (mirror the CDH's required-field list, MOSAIC-adapted).

### Phase 2 — Q4 2026: run a STAC-export pilot on the 60 real records
The registry is already populated (60 datasets across ~14 living landscapes), so this phase tests the mechanical path on actual content, not a template.
6. **Run a STAC-export pilot against the 60 real records**: take the populated registry and prove the row → STAC Collection JSON path end-to-end on real data — surfacing exactly which fields are export-blocking. Anchored to the 2026 landscape-delineation and minimum-package objectives.
7. **Build the Python exporter**: registry row → STAC Collection JSON (core fields + extents + assets + `mosaic:*`). Validate with `jsonschema` against a mirrored STAC Collection schema. No npm needed.
8. **Standardize spatial-resolution units.** Spatial resolution is filled for 43/60 records but in inconsistent forms ("30m", "5000", "25000", "Village level", "Admin - MFLLs Boundary"). STAC/data-cube needs a **numeric step + unit**, so normalize values to `{value, unit}` before export.
9. **Control the Living landscape vocabulary** against the official MFL living-landscape list (~14 distinct values, currently free text). Turn the column into a dropdown tied to the official list — directly supports the landscape-delineation objective.
10. **Populate File Size and clean the Download URL field** so both become true STAC values. File Size is filled for only 1/60 (populate → `file:size`); Download URL is filled for 56/60 but mixes real URLs with free text like "Internal" (clean → asset `href`).
11. **Mirror the CDH schemas/vocab** (read-only) into a MOSAIC `spec/` folder for reference and to keep the crosswalk current. **[COORD]** agree how MOSAIC tracks CDH version bumps.
12. **Draft the `mosaic:*` extension** (small: theme, landscape, access_level, migration_status, update_frequency) as a schema-defined JSON, following the CDH's pattern.

### Phase 3 — 2027 (scoped, not built in 2026): the real catalog & live cross-linking
13. Stand up a **static STAC catalog** (JSON + STAC Browser is static-hostable; no npm runtime needed to serve it) generated from the registry export.
14. **Implement cross-hub links** to CDH Collections (`rel=related`/`via`/`derived_from`) so climate layers resolve to the CDH as source of truth. **[COORD]** agree stable CDH Collection URLs and the link convention.
15. **Establish the shared-vocab version line** as live joint governance with the CDH. **[COORD]**

### What is explicitly NOT 2026 scope
A harmonized central repository, a full/served STAC server and hosted STAC API, item-level metadata (the CDH itself has not implemented item-level yet), and the climate block. These wait for 2027+. (The interim registry is already populated with 60 real records — what is deferred is the *served catalog and API*, not the data.)

---

## 7. Open questions / decisions for Lizeth

1. **Endorse STAC as MOSAIC's target standard now?** Adopting STAC (with the `encoding` routing) is the decision everything else hangs on. Recommended: yes — but it is a strategic commitment worth confirming with Kettle/Gaisberger because it shapes every future deliverable.

2. **How tightly to bind to the CDH's draft (v0.0.1)?** The CDH is explicitly pre-stable with breaking changes expected. Decision: align to the *concepts and standard parts* (STAC core, UN M49, SPDX) now, but treat the `cgiar-cdh` extension and CDH vocab as a moving target we *mirror*, not *depend on*, until they stabilize. Confirm with Brayden their expected timeline to a stable v1.

3. **Who owns the shared-vocabulary version line?** True interoperability needs one agreed, jointly versioned set of must-match vocabularies (geography, license, contact roles). Decision needed: does MOSAIC adopt the CDH's files directly (CDH-owned), co-own them, or maintain a mirror with an agreed sync cadence? This is the one governance question that requires a real conversation with Brayden.

4. **Scope of the `mosaic:*` custom extension.** Confirm the minimal field list (theme, landscape, access_level, migration_status, update_frequency) — keep it small, like the CDH did. Anything we can push into a standard STAC extension instead, we should.

5. **Resourcing the Python exporter & validation.** Phase 2 needs a small amount of developer time (exporter + jsonschema checks). Decision: who builds it, and when, given Lizeth coordinates rather than produces? Candidate: a focal point with Python skills, or a short scoped task.

---

### Annex — who contributed
This assessment was produced by the MOSAIC coordination team: **documentation-expert** (field-by-field crosswalk, §3; prose and assembly), **product-manager** (recommendations §4 and 2026 roadmap §6, aligned to MOSAIC's 2026 objectives and coordinate-not-produce role), and **frontend-developer** (technical feasibility for §5–6: npm-blocked toolchain constraints, `pystac` availability, Excel→STAC export feasibility). Synthesized and reconciled by the MOSAIC coordinator. Source material: MOSAIC registry schema; CDH `metadata` repo README/CONTRIBUTING; `full-standard.yaml`; `mapping-stac.md`; `crosswalk.md` (CDH v0.0.1, draft).
