"""Transformation rules (R1-R9) from spec/field_mapping.md.

Each function is pure and testable. They turn one messy registry row into the
cleaned values shared by both the frontend record and the STAC item, and they
emit data-quality flags rather than crashing on bad data.
"""
from __future__ import annotations

import re
from typing import Optional

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
EXT_RE = re.compile(r"\.([A-Za-z0-9]{1,5})(?=[\s,;]|$)")
YEAR_RE = re.compile(r"(19|20)\d{2}")

EXT_MAP = {
    "tif": "GeoTIFF", "tiff": "GeoTIFF", "shp": "Shapefile", "gpkg": "GeoPackage",
    "csv": "CSV", "xlsx": "XLSX", "xls": "XLSX", "nc": "NetCDF", "geojson": "GeoJSON",
    "json": "JSON", "zarr": "Zarr", "parquet": "Parquet", "sol": "DSSAT-SOL",
}
DATATYPE_FALLBACK = {
    "Raster": ["GeoTIFF"], "Vector": ["Shapefile"],
    "Tabular": ["CSV"], "Mixed": ["Mixed"],
}

# Placeholder/instruction strings that indicate the registry's example row.
PLACEHOLDER_TOKENS = {
    "auto-filled by formula — do not edit", "short descriptive name",
    "select from dropdown", "the mfl programme territory this dataset covers",
    "raster / vector / tabular / mixed",
}


def s(v) -> Optional[str]:
    """Normalize a cell to a trimmed string or None (treats empty/'None'/'NA')."""
    if v is None:
        return None
    t = str(v).strip()
    if t == "" or t.lower() in ("none", "nan"):
        return None
    return t


def is_placeholder_row(row) -> bool:
    """True if a row is the registry's example/instructions row."""
    rec_id = s(row[0])
    if rec_id is None:
        # blank id alone isn't enough (a real malformed row also lacks an id);
        # only treat as placeholder if other cells carry the instruction text.
        pass
    for cell in row:
        t = s(cell)
        if t and t.lower() in PLACEHOLDER_TOKENS:
            return True
    return False


# --- R1: contact email -------------------------------------------------------
def extract_contact_email(raw) -> tuple[Optional[str], list[str]]:
    flags: list[str] = []
    t = s(raw)
    if t:
        m = EMAIL_RE.search(t)
        if m:
            return m.group(0).lower(), flags
    flags.append("missing_contact_email")
    return None, flags


def extract_contact_name(raw) -> Optional[str]:
    """STAC-only: name portion before the first ' - ', ',', or '('."""
    t = s(raw)
    if not t:
        return None
    name = re.split(r" - |,|\(", t, maxsplit=1)[0].strip()
    return name or None


# --- R2: formats -------------------------------------------------------------
def derive_formats(filenames, data_type) -> tuple[list[str], list[str]]:
    flags: list[str] = []
    fn = s(filenames)
    formats: list[str] = []
    if fn:
        for ext in EXT_RE.findall(fn):
            fmt = EXT_MAP.get(ext.lower(), ext.upper())
            if fmt not in formats:
                formats.append(fmt)
    if not formats:
        dt = s(data_type)
        if dt in DATATYPE_FALLBACK:
            formats = list(DATATYPE_FALLBACK[dt])
    if not formats:
        formats = ["Unknown"]
        flags.append("unknown_format")
    return formats, flags


# --- R3: license -> SPDX -----------------------------------------------------
def map_license(raw) -> tuple[Optional[str], Optional[str], list[str]]:
    """Returns (spdx_or_value, original_alias_if_non_spdx, flags)."""
    flags: list[str] = []
    t = s(raw)
    if not t:
        return None, None, ["missing_license"]
    low = t.lower()
    if "cc by-sa" in low or "cc-by-sa" in low:
        return "CC-BY-SA-4.0", None, flags
    if "cc by-nc" in low or "cc-by-nc" in low:
        return "CC-BY-NC-4.0", None, flags
    if "cc by 4.0" in low or "cc-by" in low or "cc by" in low:
        return "CC-BY-4.0", None, flags
    if "cc0" in low or "public domain" in low:
        return "CC0-1.0", None, flags
    if low.startswith("open") or "open data" in low:
        return "other", t, ["vague_license"]
    # anything else (e.g. "CGIAR Open Access", "Restricted — contact data owner",
    # "Other (specify in notes)") -> keep verbatim, flag.
    return t, t, ["non_spdx_license"]


# --- R4: temporal split (STAC) ----------------------------------------------
def split_temporal(raw) -> tuple[list, list[str]]:
    flags: list[str] = []
    t = s(raw)
    if not t:
        return [[None, None]], ["unparsed_temporal"]
    years = [m.group(0) for m in YEAR_RE.finditer(t)]
    has_present = bool(re.search(r"present|présent", t, re.IGNORECASE))
    if len(years) >= 2:
        start, end = years[0], years[-1]
        return [[f"{start}-01-01T00:00:00Z", f"{end}-12-31T23:59:59Z"]], flags
    if len(years) == 1:
        y = years[0]
        end = None if has_present else f"{y}-12-31T23:59:59Z"
        if has_present:
            flags.append("open_ended_temporal")
        return [[f"{y}-01-01T00:00:00Z", end]], flags
    return [[None, None]], ["unparsed_temporal"]


# --- R5: spatial resolution --------------------------------------------------
NUMERIC_RES_RE = re.compile(r"^\s*\d+(\.\d+)?\s*(m|km|°|deg)?\s*$", re.IGNORECASE)


def check_resolution(raw) -> tuple[Optional[str], list[str]]:
    t = s(raw)
    if not t:
        return None, []
    if NUMERIC_RES_RE.match(t):
        return t, []
    return t, ["non_numeric_resolution"]


# --- R7: readiness_status ----------------------------------------------------
def map_readiness(raw) -> tuple[str, list[str]]:
    t = s(raw)
    if t in ("Raw", "Processed", "Validated"):
        return t, []
    return "Raw", ["missing_readiness"]


# --- R8: download_url cleaning ----------------------------------------------
def clean_download_url(raw) -> tuple[Optional[str], list[str]]:
    t = s(raw)
    if not t:
        return None, []
    first = t.replace("\xa0", " ").splitlines()[0].strip()
    if re.match(r"^(https?|ftp)://", first, re.IGNORECASE):
        return first, []
    # The value may carry a URL later in the line/string (e.g. "CHIRPS data (https://...)").
    m = re.search(r"(https?|ftp)://\S+", t)
    if m:
        url = m.group(0).rstrip(").,;")
        return url, []
    return None, ["non_url_download"]


# --- R9: metadata_url (relative path to the STAC item) ----------------------
def safe_id(raw_id: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "-", raw_id)
