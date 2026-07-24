"""Read the MFL Dataset Registry and normalize each real row into a dict that
both artifacts (frontend record + STAC item) consume. Skips the placeholder row.

Since 2026-07-24 the normalization core is `normalize_fields(fields, ...)`, which
takes a plain field-dict (COL short names -> raw values) instead of a positional
Excel row. Two sources feed it:
  - this module (Excel snapshot path, via `row_to_fields`), and
  - mosaic_pipeline/records.py (records/<ID>.yaml path — the source of truth).
Both paths MUST stay byte-identical in their artifacts; do not add Excel-only or
YAML-only behavior inside normalize_fields.
"""
from __future__ import annotations

import warnings
from pathlib import Path

import openpyxl

from . import transform as T
from .config import STAC_BASE_URL
from .vocab import COUNTRY_M49, Vocab

# Excel column index (1-based) -> short name. 23 columns.
COL = {
    "record_id": 1, "title": 2, "country": 3, "theme": 4, "living_landscape": 5,
    "data_type": 6, "spatial_resolution": 7, "temporal": 8, "source": 9,
    "contact": 10, "access_level": 11, "license": 12, "processing_status": 13,
    "file_names": 14, "current_location": 15, "migration_status": 16,
    "server_path": 17, "description": 18, "date_registered": 19, "last_updated": 20,
    "update_frequency": 21, "download_url": 22, "file_size": 23,
}

SHEET_NAME = " Registry"  # leading space is intentional

VALID_THEMES = {
    "Boundaries / admin units", "Land cover / land use", "Ecosystem condition",
    "Degradation / land health", "Water / hydrology", "Biodiversity / ecosystems",
    "Pressures / drivers", "Ecosystem services", "Hotspots / leverage points",
    "Scenarios / future risks", "Decision-support outputs",
    "Agrobiodiversity / crops", "Socio-economic / livelihoods",
}
VALID_DATA_TYPES = {"Raster", "Vector", "Tabular", "Mixed"}
VALID_ACCESS = {"Open", "Internal", "Restricted"}
# Legacy/source spellings normalized to the canonical access values above.
ACCESS_ALIASES = {"CGIAR-internal": "Internal", "CGIAR internal": "Internal"}
VALID_UPDATE_FREQ = {"Annual", "Seasonal", "Monthly", "On-demand", "Static", "Unknown"}

# Themes for which MOSAIC links to the CDH ("connect, don't duplicate").
CLIMATE_LINKED_THEMES = {"Water / hydrology", "Scenarios / future risks"}
CDH_PLACEHOLDER_URL = "https://climate-data-hub.cgiar.org/"  # [COORD] confirm with Brayden


def _g(row, key):
    return row[COL[key] - 1]


def row_to_fields(row) -> dict:
    """Positional Excel row -> field-dict keyed by COL short names (raw values)."""
    return {key: _g(row, key) for key in COL}


def read_registry(xlsx_path: str, vocab: Vocab) -> list[dict]:
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # silence "Data Validation extension..."
        wb = openpyxl.load_workbook(xlsx_path, data_only=True)
    ws = wb[SHEET_NAME]

    raw_rows = list(ws.iter_rows(min_row=2, values_only=True))
    records: list[dict] = []
    used_ids: set[str] = set()
    seq = 0  # for generated ids

    # First pass: find the highest existing MFL-2026-NNN to start generation after it.
    import re
    max_existing = 0
    for row in raw_rows:
        rid = T.s(_g(row, "record_id"))
        if rid:
            m = re.match(r"MFL-2026-(\d+)$", rid)
            if m:
                max_existing = max(max_existing, int(m.group(1)))
    seq = max_existing

    for row in raw_rows:
        if all(T.s(c) is None for c in row):
            continue  # fully empty row
        if T.is_placeholder_row(row):
            continue

        rec = normalize_fields(row_to_fields(row), vocab, used_ids,
                               lambda: _next_id(seq + 1))
        if rec.get("_used_seq"):
            seq += 1
            rec.pop("_used_seq")
        used_ids.add(rec["id"])
        records.append(rec)

    return records


def _next_id(n: int) -> str:
    return f"MFL-2026-{n:03d}"


def normalize_fields(fields: dict, vocab: Vocab, used_ids: set[str], gen_id) -> dict:
    """Normalize one record from a raw field-dict (COL short names -> raw values).

    Shared by the Excel path (row_to_fields) and the YAML records path
    (records.py). Values may come in as Excel cell scalars or YAML scalars;
    every consumer below runs them through T.s()/the R1-R9 extractors, so
    both sources normalize identically.
    """
    flags: list[str] = []

    # --- malformed "Soil dataset" detection ---
    country_raw = T.s(fields["country"])
    theme_raw = T.s(fields["theme"])
    dtype_raw = T.s(fields["data_type"])
    is_malformed = (country_raw == "Soil dataset" or theme_raw == "Soil dataset")
    if is_malformed:
        flags.append("malformed_row")

    # --- R6: id ---
    used_seq = False
    rid = T.s(fields["record_id"])
    if not rid:
        rid = gen_id()
        used_seq = True
        flags.append("generated_id")
    rid = rid.strip()
    if rid in used_ids:
        base = rid
        n = 2
        while f"{base}-{n}" in used_ids:
            n += 1
        rid = f"{base}-{n}"
        flags.append("duplicate_id")

    # --- title ---
    title = T.s(fields["title"])
    if is_malformed and title == "Soil dataset":
        # Use the description to give it a usable title rather than "Soil dataset".
        desc = T.s(fields["description"]) or ""
        title = ("Soil dataset (needs repair) — " + desc[:50]).strip() if desc else f"Soil dataset (needs repair) [{rid}]"
    if not title:
        title = f"Untitled dataset ({rid})"
        flags.append("missing_title")

    # --- country ---
    country = None if (is_malformed or country_raw == "Soil dataset") else country_raw
    if country and country not in COUNTRY_M49:
        flags.append("noncanonical_country")

    # --- living landscape (CODE + coverage) ---
    ll_code, coverage, ll_flags = vocab.resolve_landscape(fields["living_landscape"], country)
    flags += ll_flags

    # --- theme ---
    theme = None if (is_malformed or theme_raw == "Soil dataset") else theme_raw
    if theme and theme not in VALID_THEMES:
        flags.append("noncanonical_theme")

    # --- data type ---
    data_type = None if (is_malformed or dtype_raw == "Soil dataset") else dtype_raw
    if data_type and data_type not in VALID_DATA_TYPES:
        flags.append("noncanonical_data_type")

    # --- resolution (R5) ---
    spatial_resolution, res_flags = T.check_resolution(fields["spatial_resolution"])
    flags += res_flags

    # --- temporal ---
    temporal_raw = T.s(fields["temporal"])
    temporal_interval, temp_flags = T.split_temporal(fields["temporal"])
    flags += temp_flags

    # --- source ---
    source = T.s(fields["source"])

    # --- contact (R1) ---
    contact_email, c_flags = T.extract_contact_email(fields["contact"])
    flags += c_flags
    contact_name = T.extract_contact_name(fields["contact"])

    # --- access level ---
    access = T.s(fields["access_level"])
    access = ACCESS_ALIASES.get(access, access)
    if access and access not in VALID_ACCESS:
        access = None
        flags.append("noncanonical_access_level")

    # --- license (R3) ---
    license_id, license_alias, lic_flags = T.map_license(fields["license"])
    flags += lic_flags

    # --- readiness (R7) ---
    readiness, r_flags = T.map_readiness(fields["processing_status"])
    flags += r_flags

    # --- formats (R2) ---
    formats, f_flags = T.derive_formats(fields["file_names"], fields["data_type"] if not is_malformed else None)
    flags += f_flags

    # --- description ---
    description = T.s(fields["description"]) or ""

    # --- download url (R8) ---
    download_url, d_flags = T.clean_download_url(fields["download_url"])
    flags += d_flags
    download_raw = T.s(fields["download_url"])

    # --- current location / server path (STAC asset hrefs) ---
    current_location = T.s(fields["current_location"])
    server_path = T.s(fields["server_path"])

    # --- operational mosaic:* fields ---
    migration_status = T.s(fields["migration_status"])
    update_frequency = T.s(fields["update_frequency"]) or "Unknown"
    if update_frequency not in VALID_UPDATE_FREQ:
        update_frequency = "Unknown"

    date_registered = T.s(fields["date_registered"])
    last_updated = T.s(fields["last_updated"])
    file_size = fields["file_size"]

    # --- bbox (delineation-derived for landscape coverage; locator otherwise) ---
    bbox, centroid, approx = vocab.bbox_for(ll_code, country, coverage)
    if not contact_email:
        pass  # already flagged

    # --- CRS: never present in registry ---
    flags.append("missing_crs")

    # --- metadata_url (R9): absolute URL to the published STAC item ---
    safe = T.safe_id(rid)
    metadata_url = f"{STAC_BASE_URL}/collections/{ll_code}/items/{safe}.json"

    is_climate_linked = theme in CLIMATE_LINKED_THEMES

    return {
        "id": rid,
        "_safe_id": safe,
        "title": title,
        "country": country,
        "living_landscape": ll_code,
        "coverage": coverage,
        "mfl_theme": theme,
        "data_type": data_type,
        "spatial_resolution": spatial_resolution,
        "temporal_coverage": temporal_raw,
        "temporal_interval": temporal_interval,
        "source": source,
        "contact": contact_email,
        "contact_name": contact_name,
        "access_level": access,
        "license": license_id,
        "license_alias": license_alias,
        "readiness_status": readiness,
        "formats": formats,
        "description": description,
        "download_url": download_url,
        "download_raw": download_raw,
        "current_location": current_location,
        "server_path": server_path,
        "migration_status": migration_status,
        "update_frequency": update_frequency,
        "date_registered": date_registered,
        "last_updated": last_updated,
        "file_size": file_size,
        "metadata_url": metadata_url,
        "bbox": bbox,
        "centroid": centroid,
        "bbox_approximate": approx,
        "is_climate_linked": is_climate_linked,
        "cdh_link": CDH_PLACEHOLDER_URL if is_climate_linked else None,
        "flags": flags,
        "_used_seq": used_seq,
    }
