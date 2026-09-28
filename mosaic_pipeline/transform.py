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
# SPDX ids R3 can emit (checked against SPDX License List 3.29, 2026-09-23).
# CC IGO ports exist only at 3.0, and SPDX has no CC-BY-ND-3.0-IGO.
_CC_VERSIONS = ("1.0", "2.0", "2.5", "3.0", "4.0")
SPDX_LICENSE_IDS = frozenset(
    [f"CC-BY{e}-{v}" for e in ("", "-SA", "-NC", "-NC-SA", "-NC-ND", "-ND")
     for v in _CC_VERSIONS]
    + [f"CC-BY{e}-3.0-IGO" for e in ("", "-SA", "-NC", "-NC-SA", "-NC-ND")]
    + ["CC0-1.0", "ODC-By-1.0", "ODbL-1.0", "PDDL-1.0"]
)

# "CC BY-NC-SA 4.0", "CC-BY-4.0", "(CC BY-IGO)": group 1 = the element chain.
_CC_ABBR_RE = re.compile(r"\bcc[\s_-]*by(?![a-z])((?:[\s_-]*(?:nc|sa|nd|igo)(?![a-z]))*)")
_CC_VERSION_RE = re.compile(r"(?<![\d.])(\d\.\d)(?![\d.])")


def _cc_by_spdx(low: str) -> tuple[bool, Optional[str]]:
    """(names a CC BY-family license?, its SPDX id, or None if SPDX lists no such id).

    Reads the abbreviated form ("CC BY-NC-SA 4.0") and the long form ("Creative
    Commons Attribution-NonCommercial-ShareAlike 4.0 International"). No version
    -> 4.0, except IGO, which exists only as 3.0.
    """
    abbr = _CC_ABBR_RE.search(low)
    long_pos = low.find("creative commons") if "attribution" in low else -1
    if not abbr and long_pos < 0:
        return False, None
    elements = set(re.findall(r"nc|sa|nd|igo", abbr.group(1))) if abbr else set()
    if long_pos >= 0:
        if re.search(r"non[\s-]?commercial", low):
            elements.add("nc")
        if re.search(r"share[\s-]?alike", low):
            elements.add("sa")
        if re.search(r"no[\s-]?deriv", low):
            elements.add("nd")
    if "intergovernmental" in low or re.search(r"\bigo\b", low):
        elements.add("igo")
    start = min(p for p in (abbr.start() if abbr else -1, long_pos) if p >= 0)
    m = _CC_VERSION_RE.search(low, start)
    version = m.group(1) if m else ("3.0" if "igo" in elements else "4.0")
    spdx = ("CC-BY" + "".join(f"-{e.upper()}" for e in ("nc", "sa", "nd") if e in elements)
            + f"-{version}" + ("-IGO" if "igo" in elements else ""))
    return True, (spdx if spdx in SPDX_LICENSE_IDS else None)


def _odc_spdx(low: str) -> tuple[bool, Optional[str]]:
    """(names an Open Data Commons license?, its SPDX id or None). All are 1.0 only."""
    if re.search(r"\bodbl\b", low) or "open database licen" in low:
        return True, "ODbL-1.0"
    if re.search(r"\bodc[\s_-]*by\b", low) or "open data commons attribution" in low:
        return True, "ODC-By-1.0"
    if re.search(r"\bpddl\b", low) or "public domain dedication and licen" in low:
        return True, "PDDL-1.0"
    if "open data commons" in low or re.search(r"\bodc\b", low):
        return True, None
    return False, None


def map_license(raw) -> tuple[Optional[str], Optional[str], list[str]]:
    """Returns (spdx_or_value, original_alias_if_non_spdx, flags)."""
    flags: list[str] = []
    t = s(raw)
    if not t:
        return None, None, ["missing_license"]
    low = t.lower()
    # Deliberate restrictive wording (project rule: GADM, WDPA, IUCN, OSM/ODbL)
    # is never reduced to an SPDX id, even when it names one.
    if low.startswith("restricted"):
        return t, t, ["non_spdx_license"]
    # Before CC (ODC-By says "Attribution"), public domain (PDDL) and the vague
    # branch (the names start "Open Data Commons" / "Open Database").
    for parse in (_odc_spdx, _cc_by_spdx):
        named, spdx = parse(low)
        if named:
            if spdx:
                return spdx, None, flags
            # a combination SPDX does not list (e.g. CC BY-ND 3.0 IGO) -> verbatim
            return t, t, ["non_spdx_license"]
    if "cc0" in low or "public domain" in low:
        return "CC0-1.0", None, flags
    if low.startswith("open") or "open data" in low:
        return "other", t, ["vague_license"]
    # anything else (e.g. "CGIAR Open Access", "Other (specify in notes)")
    # -> keep verbatim, flag.
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
