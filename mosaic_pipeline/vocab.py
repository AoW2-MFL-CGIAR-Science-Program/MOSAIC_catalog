"""Controlled-vocabulary lookups: living-landscape crosswalk, country -> M49/ISO3,
approximate bbox lookup. Loads the spec/*.json files and applies the agreed
additions (COL-NAT / PER-NAT) per the crosswalk's expected_codes note.
"""
from __future__ import annotations

import json
from pathlib import Path

SPEC_DIR = Path(__file__).resolve().parent.parent / "spec"

# Country display -> (UN M49 kebab id, ISO3). From vocab_reconciliation.md §1.
COUNTRY_M49 = {
    "Colombia": ("colombia", "COL"),
    "Côte d'Ivoire": ("cote-d-ivoire", "CIV"),
    "Ethiopia": ("ethiopia", "ETH"),
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


def _load(name: str) -> dict:
    with open(SPEC_DIR / name, encoding="utf-8") as f:
        return json.load(f)


class Vocab:
    """Holds all crosswalks and records any codes/bboxes added at runtime."""

    def __init__(self) -> None:
        cw = _load("living_landscape_crosswalk.json")
        self.ll_by_text: dict[str, dict] = {}
        for entry in cw["landscapes"]:
            key = entry["free_text"].strip().lower()
            self.ll_by_text[key] = entry

        bb = _load("bbox_lookup.json")
        self.bbox_landscapes: dict[str, dict] = bb["landscapes"]
        self.bbox_country: dict[str, dict] = bb["country_fallback"]

        # Runtime additions reported back to the standards specialist / Lizeth.
        self.added_codes: list[dict] = []

    # --- living landscape -----------------------------------------------------
    def resolve_landscape(self, raw_ll, country) -> tuple[str, list[str]]:
        """Returns (CODE, flags). Applies the crosswalk; adds COUNTRY3-NAT
        entries for known countries whose value didn't resolve to a real place."""
        flags: list[str] = []
        from .transform import s
        text = s(raw_ll)
        ctry = s(country)

        if text:
            entry = self.ll_by_text.get(text.strip().lower())
            if entry:
                code = entry["code"]
                # "Country and basin scale" / generic -> GLB-UNSPEC in the crosswalk,
                # but if we know the country, use the national fallback code instead.
                if code == "GLB-UNSPEC" and ctry in COUNTRY_M49 and ctry != "Soil dataset":
                    code = self._ensure_national_code(ctry)
                    flags.append("unspecified_landscape_mapped_to_national")
                return code, flags

        # Unmatched free text.
        if ctry in COUNTRY_M49:
            code = self._ensure_national_code(ctry)
            flags.append("unmatched_living_landscape")
            return code, flags
        flags.append("unmatched_living_landscape")
        return "GLB-UNSPEC", flags

    def _ensure_national_code(self, country: str) -> str:
        iso3 = COUNTRY_M49[country][1]
        code = f"{iso3}-NAT"
        if code not in self.bbox_landscapes:
            # Derive a bbox for the national code from the country fallback.
            cf = self.bbox_country.get(country)
            if cf:
                self.bbox_landscapes[code] = {
                    "bbox": cf["bbox"], "centroid": cf["centroid"],
                    "name": f"{country} (national)",
                }
                self.added_codes.append({
                    "code": code, "country": country,
                    "reason": "Landscape value was country/scale-level only; "
                              "added national code with country-fallback bbox.",
                })
        return code

    # --- bbox -----------------------------------------------------------------
    def bbox_for(self, code: str, country) -> tuple[list, list, bool]:
        """Returns (bbox, centroid, approximate_flag)."""
        from .transform import s
        ctry = s(country)
        if code in self.bbox_landscapes:
            e = self.bbox_landscapes[code]
            return e["bbox"], e["centroid"], True
        if ctry and ctry in self.bbox_country:
            e = self.bbox_country[ctry]
            return e["bbox"], e["centroid"], True
        e = self.bbox_landscapes["GLB-UNSPEC"]
        return e["bbox"], e["centroid"], True

    def landscape_name(self, code: str) -> str:
        if code in self.bbox_landscapes:
            return self.bbox_landscapes[code].get("name", code)
        return code

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
