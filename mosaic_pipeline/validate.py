"""Lightweight STAC validator in pure Python (jsonschema not installed; npm blocked).

Mirrors the required-field checks of the STAC Catalog / Collection / Item core
schemas. This is intentionally a structural check, not a full JSON-Schema run.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

_RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|\+00:00)$")


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
    # STAC: an Item must have datetime OR (start_datetime AND end_datetime), all RFC 3339.
    has_dt = props.get("datetime") is not None
    has_range = bool(props.get("start_datetime")) and bool(props.get("end_datetime"))
    if not (has_dt or has_range):
        errs.append(_err(path, "properties needs datetime or start/end_datetime"))
    for k in ("datetime", "start_datetime", "end_datetime", "created", "updated"):
        v = props.get(k)
        if k in props and not (v is None and k == "datetime") and not (
                isinstance(v, str) and _RFC3339.match(v)):
            errs.append(_err(path, f"{k} must be an RFC 3339 UTC timestamp, got {v!r}"))
    assets = obj.get("assets")
    if not isinstance(assets, dict):
        errs.append(_err(path, "assets must be an object (it may be empty)"))
    else:
        for key, asset in assets.items():
            if not (isinstance(asset, dict) and asset.get("href")):
                errs.append(_err(path, f"asset '{key}' needs a non-empty href"))
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
