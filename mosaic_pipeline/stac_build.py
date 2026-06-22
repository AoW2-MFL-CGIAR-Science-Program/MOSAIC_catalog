"""Artifact A: build a static STAC catalog tree (plain JSON, no pystac).

Structure:
  stac/catalog.json                       (root Catalog)
  stac/collections/<CODE>/collection.json (one per living-landscape code)
  stac/collections/<CODE>/items/<id>.json (one per dataset)

Uses cgiar-cdh:* and mosaic:* namespaces per MOSAIC_CDH_Interoperability_STAC_
Assessment_202606.md. Approximate bboxes are flagged. Climate-themed items link
to the CDH via links[rel=via|related] rather than re-describing them.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from .config import STAC_BASE_URL
from .vocab import COUNTRY_M49, Vocab

STAC_VERSION = "1.0.0"
MOSAIC_SCHEMA_VERSION = "0.1.0"

# Custom extension identifiers (mirrored locally; schemas hosted later).
EXT_MOSAIC = "https://mosaic.cgiar.org/stac-extensions/mosaic/v0.1.0/schema.json"
EXT_CDH = "https://climate-data-hub.cgiar.org/stac-extensions/cgiar-cdh/v1.0.0/schema.json"

MEDIA_TYPE = {
    "GeoTIFF": "image/tiff; application=geotiff",
    "GeoPackage": "application/geopackage+sqlite3",
    "GeoJSON": "application/geo+json",
    "NetCDF": "application/x-netcdf",
    "CSV": "text/csv",
    "XLSX": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "JSON": "application/json",
    "Shapefile": "application/octet-stream",
}


def _self_link(path_from_root: str) -> dict:
    return {"rel": "self", "href": path_from_root}


def build_stac(records: list[dict], vocab: Vocab, stac_dir: Path) -> dict:
    """Writes the full tree. Returns a small summary dict."""
    if stac_dir.exists():
        shutil.rmtree(stac_dir)  # idempotent: wipe and rebuild
    (stac_dir / "collections").mkdir(parents=True, exist_ok=True)

    # Group records by living-landscape code.
    by_code: dict[str, list[dict]] = {}
    for r in records:
        by_code.setdefault(r["living_landscape"], []).append(r)

    n_items = 0
    catalog_links = [
        {"rel": "root", "href": "./catalog.json", "type": "application/json"},
        # self is ABSOLUTE (citable endpoint); internal nav links stay relative.
        {"rel": "self", "href": f"{STAC_BASE_URL}/catalog.json", "type": "application/json"},
    ]

    for code in sorted(by_code):
        recs = by_code[code]
        coll_dir = stac_dir / "collections" / code
        (coll_dir / "items").mkdir(parents=True, exist_ok=True)

        collection = _build_collection(code, recs, vocab)
        item_links = []
        for r in recs:
            item = _build_item(r, code, vocab)
            item_path = coll_dir / "items" / f"{r['_safe_id']}.json"
            _write_json(item_path, item)
            n_items += 1
            item_links.append({
                "rel": "item",
                "href": f"./items/{r['_safe_id']}.json",
                "type": "application/json",
                "title": r["title"],
            })
        collection["links"] = [
            {"rel": "root", "href": "../../catalog.json", "type": "application/json"},
            {"rel": "parent", "href": "../../catalog.json", "type": "application/json"},
            {"rel": "self",
             "href": f"{STAC_BASE_URL}/collections/{code}/collection.json",
             "type": "application/json"},
        ] + item_links
        _write_json(coll_dir / "collection.json", collection)

        catalog_links.append({
            "rel": "child",
            "href": f"./collections/{code}/collection.json",
            "type": "application/json",
            "title": vocab.landscape_name(code),
        })

    catalog = {
        "type": "Catalog",
        "stac_version": STAC_VERSION,
        "id": "mosaic-mfl-catalog",
        "title": "MOSAIC — MFL Multifunctional Landscapes Catalog",
        "description": (
            "MOSAIC coordination-network metadata catalog for the CGIAR MFL Science "
            "Programme (AoW2). One STAC Collection per Living Landscape, one Item per "
            "registered dataset. Spatial extents are APPROXIMATE locator boxes pending "
            "the 2026 landscape-delineation work. Climate layers link to the CGIAR "
            "Climate Data Hub (connect, don't duplicate)."
        ),
        "links": catalog_links,
        "mosaic:schema_version": MOSAIC_SCHEMA_VERSION,
    }
    _write_json(stac_dir / "catalog.json", catalog)

    return {
        "collections": len(by_code),
        "items": n_items,
        "codes": sorted(by_code),
    }


def _collect_temporal(recs: list[dict]) -> list:
    starts, ends = [], []
    for r in recs:
        iv = r["temporal_interval"][0]
        if iv[0]:
            starts.append(iv[0])
        if iv[1]:
            ends.append(iv[1])
    start = min(starts) if starts else None
    end = max(ends) if ends else None
    return [[start, end]]


def _union_bbox(recs: list[dict]) -> list:
    boxes = [r["bbox"] for r in recs if r.get("bbox")]
    if not boxes:
        return [-180.0, -90.0, 180.0, 90.0]
    w = min(b[0] for b in boxes)
    s = min(b[1] for b in boxes)
    e = max(b[2] for b in boxes)
    n = max(b[3] for b in boxes)
    return [w, s, e, n]


def _build_collection(code: str, recs: list[dict], vocab: Vocab) -> dict:
    bbox = _union_bbox(recs)
    temporal = _collect_temporal(recs)

    # Geography (UN M49) union across member items.
    geos: list[str] = []
    for r in recs:
        for g in COUNTRY_M49.get(r["country"], (None,))[:1] if r["country"] in COUNTRY_M49 else []:
            if g and g not in geos:
                geos.append(g)
    geographies = sorted({COUNTRY_M49[r["country"]][0] for r in recs if r["country"] in COUNTRY_M49})

    themes = sorted({r["mfl_theme"] for r in recs if r["mfl_theme"]})
    access_levels = sorted({r["access_level"] for r in recs if r["access_level"]})

    # Collection license: if all members share one SPDX id use it, else "various".
    lics = {r["license"] for r in recs if r["license"]}
    if len(lics) == 1:
        license_val = next(iter(lics))
        # STAC license must be SPDX or "other"/"proprietary"; non-SPDX -> "other".
        if not _looks_spdx(license_val):
            license_val = "other"
    elif lics:
        license_val = "other"
    else:
        license_val = "other"

    coll = {
        "type": "Collection",
        "stac_version": STAC_VERSION,
        "stac_extensions": [EXT_MOSAIC, EXT_CDH],
        "id": code,
        "title": vocab.landscape_name(code),
        "description": (
            f"Datasets registered under the '{vocab.landscape_name(code)}' Living "
            f"Landscape ({len(recs)} item(s)). Spatial extent is an APPROXIMATE "
            f"locator box, not a survey-grade boundary."
        ),
        "license": license_val,
        "extent": {
            "spatial": {"bbox": [bbox]},
            "temporal": {"interval": temporal},
        },
        "keywords": themes,
        "providers": _collection_providers(recs),
        "summaries": {
            "mosaic:access_level": access_levels,
            "mosaic:theme": themes,
        },
        "cgiar-cdh:geography": geographies,
        "mosaic:living_landscape": code,
        "mosaic:bbox_approximate": True,
        "mosaic:bbox_note": (
            "Approximate locator box from MOSAIC bbox_lookup (EPSG:4326). To be "
            "replaced by delineated boundaries (2026 objective)."
        ),
        "mosaic:item_count": len(recs),
        "links": [],  # filled by caller
    }
    return coll


def _looks_spdx(value: str) -> bool:
    spdx = {"CC-BY-4.0", "CC-BY-SA-4.0", "CC-BY-NC-4.0", "CC0-1.0", "other"}
    return value in spdx


def _collection_providers(recs: list[dict]) -> list[dict]:
    names = sorted({r["source"] for r in recs if r["source"]})
    return [{"name": n, "roles": ["producer"]} for n in names] or [
        {"name": "MOSAIC / CGIAR MFL Science Programme", "roles": ["host"]}
    ]


def _build_item(r: dict, code: str, vocab: Vocab) -> dict:
    bbox = r["bbox"]
    geometry = _bbox_to_polygon(bbox)

    geography, _ = Vocab.country_m49(r["country"])

    props = {
        "title": r["title"],
        "description": r["description"],
        "datetime": None,  # closed interval below; null datetime is valid with start/end
        "start_datetime": r["temporal_interval"][0][0],
        "end_datetime": r["temporal_interval"][0][1],
        "created": r["date_registered"],
        "updated": r["last_updated"],
        # cgiar-cdh:* (CDH-defined where applicable)
        "cgiar-cdh:geography": geography,
        "cgiar-cdh:spatial_resolution": r["spatial_resolution"],
        # mosaic:* (MOSAIC-specific)
        "mosaic:living_landscape": code,
        "mosaic:theme": r["mfl_theme"],
        "mosaic:access_level": r["access_level"],
        "mosaic:processing_status": r["readiness_status"],
        "mosaic:migration_status": r["migration_status"],
        "mosaic:update_frequency": r["update_frequency"],
        "mosaic:bbox_approximate": r["bbox_approximate"],
        "mosaic:formats": r["formats"],
    }
    # proj: CRS unknown in registry -> explicit null + note.
    props["proj:code"] = None
    props["mosaic:crs_note"] = "CRS not recorded in registry (missing_crs)."

    if r["license_alias"] and not _looks_spdx(r["license"] or ""):
        props["mosaic:license_original"] = r["license_alias"]

    if r["contact"] or r["contact_name"]:
        props["contacts"] = [{
            "name": r["contact_name"] or r["contact"] or "Unknown",
            "emails": ([{"value": r["contact"]}] if r["contact"] else []),
            "roles": ["producer", "licensor"],
        }]

    # Drop None datetime keys that STAC validators dislike? datetime=null is allowed
    # when start/end present, so keep it.

    assets = _build_assets(r)

    links = [
        {"rel": "root", "href": "../../../catalog.json", "type": "application/json"},
        {"rel": "parent", "href": "../collection.json", "type": "application/json"},
        {"rel": "collection", "href": "../collection.json", "type": "application/json"},
        {"rel": "self",
         "href": f"{STAC_BASE_URL}/collections/{code}/items/{r['_safe_id']}.json",
         "type": "application/json"},
    ]
    if r["download_url"]:
        links.append({"rel": "via", "href": r["download_url"], "title": "Primary source / download"})
    # connect, don't duplicate: climate layers point at the CDH.
    if r["is_climate_linked"] and r["cdh_link"]:
        links.append({
            "rel": "related",
            "href": r["cdh_link"],
            "title": "CGIAR Climate Data Hub (source of truth for climate layers) [placeholder URL]",
        })

    item = {
        "type": "Feature",
        "stac_version": STAC_VERSION,
        "stac_extensions": [EXT_MOSAIC, EXT_CDH],
        "id": r["id"],
        "geometry": geometry,
        "bbox": bbox,
        "properties": props,
        "collection": code,
        "links": links,
        "assets": assets,
    }
    return item


def _build_assets(r: dict) -> dict:
    assets: dict[str, dict] = {}
    primary_media = MEDIA_TYPE.get(r["formats"][0]) if r["formats"] else None

    # Primary asset href: prefer cleaned download_url, then a usable current_location.
    href = r["download_url"]
    if href:
        asset = {
            "href": href,
            "title": "Primary data source",
            "roles": ["data"],
        }
        if primary_media:
            asset["type"] = primary_media
        if r["file_size"] and str(r["file_size"]).strip().isdigit():
            asset["file:size"] = int(r["file_size"])
        assets["data"] = asset

    # Operational pointers that are not resolvable URLs become access notes, not hrefs.
    notes = []
    if r["current_location"]:
        notes.append(f"Current location: {r['current_location']}")
    if r["server_path"]:
        notes.append(f"Server path: {r['server_path']}")
    if r["download_raw"] and not r["download_url"]:
        notes.append(f"Source note: {r['download_raw']}")
    if notes:
        assets["access-note"] = {
            "href": "",
            "title": "Access note (no resolvable URL)",
            "description": " | ".join(notes),
            "roles": ["metadata"],
        }

    if not assets:
        # Items must have an assets object; provide an explicit empty-state marker.
        assets["unavailable"] = {
            "href": "",
            "title": "No download URL or location recorded",
            "roles": ["metadata"],
        }
    return assets


def _bbox_to_polygon(bbox: list) -> dict:
    w, s, e, n = bbox
    return {
        "type": "Polygon",
        "coordinates": [[[w, s], [e, s], [e, n], [w, n], [w, s]]],
    }


def _write_json(path: Path, obj: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)
        f.write("\n")
