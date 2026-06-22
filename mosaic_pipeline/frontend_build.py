"""Artifact B: build the frontend datasets.json data contract.

One flat record per dataset, using exactly the keys the frontend expects:
id, title, country, living_landscape, mfl_theme, data_type, spatial_resolution,
temporal_coverage, source, contact, access_level, license, readiness_status,
formats, description, download_url, metadata_url.
"""
from __future__ import annotations

import json
from pathlib import Path

FRONTEND_KEYS = [
    "id", "title", "country", "living_landscape", "mfl_theme", "data_type",
    "spatial_resolution", "temporal_coverage", "source", "contact",
    "access_level", "license", "readiness_status", "formats", "description",
    "download_url", "metadata_url",
]


def build_frontend(records: list[dict], out_path: Path) -> int:
    out = []
    for r in records:
        out.append({
            "id": r["id"],
            "title": r["title"],
            "country": r["country"],
            "living_landscape": r["living_landscape"],
            "mfl_theme": r["mfl_theme"],
            "data_type": r["data_type"],
            "spatial_resolution": r["spatial_resolution"],
            "temporal_coverage": r["temporal_coverage"],
            "source": r["source"],
            "contact": r["contact"],
            "access_level": r["access_level"],
            "license": r["license"],
            "readiness_status": r["readiness_status"],
            "formats": r["formats"],
            "description": r["description"],
            "download_url": r["download_url"],
            "metadata_url": r["metadata_url"],
        })
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
        f.write("\n")
    return len(out)
