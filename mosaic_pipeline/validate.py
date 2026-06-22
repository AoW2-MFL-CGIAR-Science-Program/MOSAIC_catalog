"""Lightweight STAC validator in pure Python (jsonschema not installed; npm blocked).

Mirrors the required-field checks of the STAC Catalog / Collection / Item core
schemas. This is intentionally a structural check, not a full JSON-Schema run.
"""
from __future__ import annotations

import json
from pathlib import Path


def _err(path: Path, msg: str) -> str:
    return f"{path.name}: {msg}"


def validate_catalog(obj: dict, path: Path) -> list[str]:
    errs = []
    for k in ("type", "stac_version", "id", "links"):
        if k not in obj:
            errs.append(_err(path, f"missing '{k}'"))
    if obj.get("type") != "Catalog":
        errs.append(_err(path, f"type should be 'Catalog', got {obj.get('type')!r}"))
    if not isinstance(obj.get("links"), list):
        errs.append(_err(path, "'links' must be a list"))
    return errs


def validate_collection(obj: dict, path: Path) -> list[str]:
    errs = []
    for k in ("type", "stac_version", "id", "description", "license", "extent", "links"):
        if k not in obj:
            errs.append(_err(path, f"missing '{k}'"))
    if obj.get("type") != "Collection":
        errs.append(_err(path, f"type should be 'Collection', got {obj.get('type')!r}"))
    ext = obj.get("extent", {})
    if "spatial" not in ext or "temporal" not in ext:
        errs.append(_err(path, "extent must have 'spatial' and 'temporal'"))
    else:
        bbox = ext["spatial"].get("bbox")
        if not (isinstance(bbox, list) and bbox and isinstance(bbox[0], list) and len(bbox[0]) == 4):
            errs.append(_err(path, "extent.spatial.bbox must be [[w,s,e,n]]"))
        iv = ext["temporal"].get("interval")
        if not (isinstance(iv, list) and iv and isinstance(iv[0], list) and len(iv[0]) == 2):
            errs.append(_err(path, "extent.temporal.interval must be [[start,end]]"))
    if not obj.get("license"):
        errs.append(_err(path, "license is empty"))
    return errs


def validate_item(obj: dict, path: Path) -> list[str]:
    errs = []
    for k in ("type", "stac_version", "id", "geometry", "bbox", "properties", "links", "assets"):
        if k not in obj:
            errs.append(_err(path, f"missing '{k}'"))
    if obj.get("type") != "Feature":
        errs.append(_err(path, f"type should be 'Feature', got {obj.get('type')!r}"))
    bbox = obj.get("bbox")
    if not (isinstance(bbox, list) and len(bbox) == 4):
        errs.append(_err(path, "bbox must be [w,s,e,n]"))
    geom = obj.get("geometry")
    if not (isinstance(geom, dict) and geom.get("type") and geom.get("coordinates")):
        errs.append(_err(path, "geometry must be a GeoJSON object"))
    props = obj.get("properties", {})
    # STAC: an Item must have datetime OR (start_datetime AND end_datetime).
    has_dt = props.get("datetime") is not None
    has_range = "start_datetime" in props and "end_datetime" in props
    if not (has_dt or has_range):
        errs.append(_err(path, "properties needs datetime or start/end_datetime"))
    if not isinstance(obj.get("assets"), dict) or not obj["assets"]:
        errs.append(_err(path, "assets must be a non-empty object"))
    return errs


def validate_tree(stac_dir: Path) -> dict:
    """Walk the tree, parse every JSON, run the right structural check.
    Returns {'passed': n, 'failed': n, 'errors': [...], 'parsed': n}."""
    errors: list[str] = []
    passed = failed = parsed = 0

    files = sorted(stac_dir.rglob("*.json"))
    for fp in files:
        try:
            obj = json.loads(fp.read_text(encoding="utf-8"))
            parsed += 1
        except Exception as e:  # noqa
            errors.append(f"{fp.name}: JSON parse error: {e}")
            failed += 1
            continue
        t = obj.get("type")
        if t == "Catalog":
            errs = validate_catalog(obj, fp)
        elif t == "Collection":
            errs = validate_collection(obj, fp)
        elif t == "Feature":
            errs = validate_item(obj, fp)
        else:
            errs = [f"{fp.name}: unknown STAC type {t!r}"]
        if errs:
            errors.extend(errs)
            failed += 1
        else:
            passed += 1

    return {"files": len(files), "parsed": parsed, "passed": passed,
            "failed": failed, "errors": errors}
