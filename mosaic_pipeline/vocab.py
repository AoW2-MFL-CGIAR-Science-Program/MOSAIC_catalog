"""Controlled-vocabulary lookups: living-landscape crosswalk, country -> M49/ISO3,
landscape bbox lookup (REAL delineation-derived boxes since 2026-07-21).

The canonical landscape list (11 delineated landscapes + NATIONAL + GLOBAL
coverage values) was approved by Lizeth on 2026-07-21. Boundaries live in
boundaries/<CODE>.geojson; bboxes in spec/bbox_lookup.json are derived from them.
"""
from __future__ import annotations

import json
from pathlib import Path

SPEC_DIR = Path(__file__).resolve().parent.parent / "spec"

# Country display -> (UN M49 kebab id, ISO3). From vocab_reconciliation.md §1.
COUNTRY_M49 = {
    "Cambodia": ("cambodia", "KHM"),
    "Colombia": ("colombia", "COL"),
    "Côte d'Ivoire": ("cote-d-ivoire", "CIV"),
    "Ethiopia": ("ethiopia", "ETH"),
    "Global": ("world", "GLB"),
    "India": ("india", "IND"),
    "Kenya": ("kenya", "KEN"),
    "Laos": ("lao-people-s-democratic-republic", "LAO"),
    "Peru": ("peru", "PER"),
    "Senegal": ("senegal", "SEN"),
    "Tanzania": ("united-republic-of-tanzania", "TZA"),
    "Tunisia": ("tunisia", "TUN"),
    "Vietnam": ("viet-nam", "VNM"),
    "Zimbabwe": ("zimbabwe", "ZWE"),
}

COUNTRY_ENUM = list(COUNTRY_M49.keys())

# Country -> canonical landscape collection for NATIONAL-coverage datasets
# ("assign to the country's landscape", decided 2026-07-21). Kenya has TWO
# landscapes; national Kenya records go to KEN-LVB as primary and the STAC
# item carries a related link to KEN-LEI (see stac_build).
COUNTRY_TO_LANDSCAPE = {
    "Colombia": "COL-CUM",
    "Côte d'Ivoire": "CIV-NZ",
    "Ethiopia": "ETH-OG",
    "India": "IND-CH",
    "Kenya": "KEN-LVB",
    "Laos": "MEK-3S",
    "Cambodia": "MEK-3S",
    "Vietnam": "MEK-3S",
    "Peru": "PER-PCL",
    "Senegal": "SEN-FK",
    "Tunisia": "TUN-NW",
    "Zimbabwe": "ZWE-MB",
}

# Countries whose datasets fold into more than one landscape collection.
MULTI_LANDSCAPE_COUNTRIES = {"Kenya": ["KEN-LVB", "KEN-LEI"]}

NATIONAL_VALUE = "NATIONAL — Country-wide coverage"
GLOBAL_VALUE = "GLOBAL — Global / cross-landscape"
GLOBAL_CODE = "GLB"


def _load(name: str) -> dict:
    with open(SPEC_DIR / name, encoding="utf-8") as f:
        return json.load(f)


class Vocab:
    """Holds all crosswalks; landscape entries carry name/system/countries."""

    def __init__(self) -> None:
        cw = _load("living_landscape_crosswalk.json")
        self.ll_by_text: dict[str, dict] = {}
        for entry in cw["landscapes"]:
            key = entry["free_text"].strip().lower()
            self.ll_by_text[key] = entry

        bb = _load("bbox_lookup.json")
        self.bbox_landscapes: dict[str, dict] = bb["landscapes"]
        self.bbox_country: dict[str, dict] = bb["country_fallback"]

        # Kept for report compatibility; canonical codes are frozen, nothing
        # is added at runtime any more.
        self.added_codes: list[dict] = []

    # --- living landscape -----------------------------------------------------
    def resolve_landscape(self, raw_ll, country) -> tuple[str, str, list[str]]:
        """Returns (CODE, coverage, flags). coverage: landscape|national|global.

        Handles the canonical controlled values ("CODE — Name", NATIONAL,
        GLOBAL) plus the legacy free-text crosswalk for robustness."""
        flags: list[str] = []
        from .transform import s
        text = s(raw_ll)
        ctry = s(country)

        code = None
        if text:
            t = text.strip()
            # Canonical "CODE — Name" values normalize by their code prefix.
            prefix = t.split("—")[0].strip() if "—" in t else t
            if prefix in self.bbox_landscapes and prefix != GLOBAL_CODE:
                return prefix, "landscape", flags
            if t == NATIONAL_VALUE or prefix == "NATIONAL":
                code = "NATIONAL"
            elif t == GLOBAL_VALUE or prefix in ("GLOBAL", GLOBAL_CODE, "GLB-UNSPEC"):
                code = GLOBAL_CODE
            else:
                entry = self.ll_by_text.get(t.lower())
                if entry:
                    code = entry["code"]

        if code is None:
            flags.append("unmatched_living_landscape")
            code = "NATIONAL" if ctry in COUNTRY_TO_LANDSCAPE else GLOBAL_CODE

        if code == "NATIONAL":
            if ctry in COUNTRY_TO_LANDSCAPE:
                assigned = COUNTRY_TO_LANDSCAPE[ctry]
                if ctry in MULTI_LANDSCAPE_COUNTRIES:
                    flags.append("national_assigned_to_primary_landscape")
                return assigned, "national", flags
            flags.append("national_without_known_country")
            return GLOBAL_CODE, "global", flags

        if code == GLOBAL_CODE:
            return GLOBAL_CODE, "global", flags

        return code, "landscape", flags

    # --- bbox -----------------------------------------------------------------
    def bbox_for(self, code: str, country, coverage: str = "landscape") -> tuple[list, list, bool]:
        """Returns (bbox, centroid, approximate_flag).

        - landscape coverage -> real delineation-derived bbox (approximate only
          in the sense that the ITEM's own extent is unknown; flag stays True
          for items, but the box itself is authoritative for the landscape).
        - national coverage  -> country locator box (approximate).
        - global coverage    -> world-ish box (approximate).
        """
        from .transform import s
        ctry = s(country)
        if coverage == "national" and ctry and ctry in self.bbox_country:
            e = self.bbox_country[ctry]
            return e["bbox"], e["centroid"], True
        if code in self.bbox_landscapes:
            e = self.bbox_landscapes[code]
            approx = not e.get("delineated", False)
            return e["bbox"], e["centroid"], approx
        if ctry and ctry in self.bbox_country:
            e = self.bbox_country[ctry]
            return e["bbox"], e["centroid"], True
        e = self.bbox_landscapes[GLOBAL_CODE]
        return e["bbox"], e["centroid"], True

    # --- landscape attributes ---------------------------------------------------
    def entry(self, code: str) -> dict:
        return self.bbox_landscapes.get(code, {})

    def landscape_name(self, code: str) -> str:
        return self.entry(code).get("name", code)

    def landscape_system(self, code: str):
        return self.entry(code).get("landscape_system")

    def landscape_countries(self, code: str) -> list[str]:
        return self.entry(code).get("countries", [])

    def is_delineated(self, code: str) -> bool:
        return bool(self.entry(code).get("delineated"))

    def pending_confirmation(self, code: str) -> bool:
        return bool(self.entry(code).get("pending_confirmation"))

    def delineated_codes(self) -> list[str]:
        return sorted(c for c, e in self.bbox_landscapes.items() if e.get("delineated"))

    # --- country --------------------------------------------------------------
    @staticmethod
    def country_m49(country) -> tuple[list[str], list[str]]:
        """Returns (cgiar-cdh:geography list, flags)."""
        from .transform import s
        c = s(country)
        if c == "Soil dataset":
            return [], ["malformed_row"]
        if c in COUNTRY_M49:
            return [COUNTRY_M49[c][0]], []
        if c is None:
            return [], []
        return [], ["unknown_country"]
