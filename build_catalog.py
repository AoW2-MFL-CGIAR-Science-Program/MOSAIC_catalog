#!/usr/bin/env python3
"""MOSAIC catalog pipeline — main entrypoint.

Reads the MFL Dataset Registry (single source of truth) and produces:
  A. A static STAC catalog tree under  MOSAIC_catalog/stac/
  B. The frontend data contract at     MOSAIC_catalog/datasets.json

Idempotent: wipes/rebuilds stac/ and overwrites datasets.json each run.

Usage:
    python3 build_catalog.py                 # build STAC + datasets.json
    python3 build_catalog.py --sync-frontend # also copy datasets.json to the frontend
"""
from __future__ import annotations

import shutil
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from mosaic_pipeline.frontend_build import build_frontend  # noqa: E402
from mosaic_pipeline.registry import read_registry  # noqa: E402
from mosaic_pipeline.stac_build import build_stac  # noqa: E402
from mosaic_pipeline.validate import validate_tree  # noqa: E402
from mosaic_pipeline.vocab import Vocab  # noqa: E402

# Absolute paths (the environment resets cwd; keep these explicit).
# The registry is committed INSIDE this repo so the build is self-contained and
# CI can rebuild it. NOTE: this Excel is a PROVISIONAL SNAPSHOT for the v1
# exercise (see catalog/SNAPSHOT_NOTE.md) and will be replaced.
REGISTRY_XLSX = HERE / "catalog" / "MFL_Dataset_Registry.xlsx"
STAC_DIR = HERE / "stac"
# Canonical datasets.json lives inside this repo, next to stac/. It is copied
# into the frontend repo as a separate, explicit step (--sync-frontend).
DATASETS_JSON = HERE / "datasets.json"
# Default frontend data path when the frontend repo sits beside this one.
DEFAULT_FRONTEND_DATASETS = (
    HERE.parent
    / "MOSAIC_frontend"
    / "mfl-living-landscapes-frontend"
    / "frontend"
    / "data"
    / "datasets.json"
)


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="MOSAIC catalog pipeline: registry -> STAC + datasets.json"
    )
    parser.add_argument(
        "--sync-frontend", nargs="?", const=str(DEFAULT_FRONTEND_DATASETS),
        default=None, metavar="PATH",
        help="After building, copy datasets.json into the frontend repo. With no "
             "PATH, uses the default sibling location. Local use only — do NOT "
             "use in the catalog repo's CI (no frontend checkout there).",
    )
    args = parser.parse_args(argv)

    print("MOSAIC catalog pipeline")
    print("=" * 60)
    print(f"Registry : {REGISTRY_XLSX}")
    print(f"STAC out : {STAC_DIR}")
    print(f"datasets : {DATASETS_JSON}")
    print("-" * 60)

    if not REGISTRY_XLSX.exists():
        print(f"ERROR: registry not found: {REGISTRY_XLSX}")
        return 1

    vocab = Vocab()
    records = read_registry(str(REGISTRY_XLSX), vocab)
    print(f"Real records read: {len(records)}")

    # --- Artifact B: datasets.json (canonical copy inside this repo) ---
    n_front = build_frontend(records, DATASETS_JSON)
    print(f"datasets.json written: {n_front} records")

    # --- Artifact A: STAC ---
    stac_summary = build_stac(records, vocab, STAC_DIR)
    print(f"STAC tree written: {stac_summary['collections']} collections, "
          f"{stac_summary['items']} items")

    # --- validation ---
    v = validate_tree(STAC_DIR)
    print("-" * 60)
    print(f"STAC validation: {v['parsed']}/{v['files']} files parsed; "
          f"{v['passed']} passed, {v['failed']} failed")
    if v["errors"]:
        print("Validation errors (first 20):")
        for e in v["errors"][:20]:
            print("  -", e)

    # --- coverage report ---
    _report(records, vocab, stac_summary)

    # --- optional: sync datasets.json into the frontend repo (the hand-off) ---
    if args.sync_frontend:
        dest = Path(args.sync_frontend)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(DATASETS_JSON, dest)
        print("-" * 60)
        print(f"Synced datasets.json -> {dest}")
        print("Next, in the frontend repo, commit & push to publish:")
        print("  git add frontend/data/datasets.json")
        print('  git commit -m "Update datasets.json from MOSAIC catalog regeneration"')
        print("  git push")

    return 0 if v["failed"] == 0 else 2


def _report(records, vocab, stac_summary) -> None:
    n = len(records)
    ll_mapped = sum(1 for r in records if r["living_landscape"] != "GLB-UNSPEC")
    bbox_assigned = sum(1 for r in records if r["bbox"])
    url_ok = sum(1 for r in records if r["download_url"])
    email_ok = sum(1 for r in records if r["contact"])
    readiness_ok = sum(1 for r in records if "missing_readiness" not in r["flags"])

    print("=" * 60)
    print("COVERAGE REPORT")
    print(f"  real records processed     : {n}")
    print(f"  living_landscape mapped    : {ll_mapped}/{n} "
          f"(GLB-UNSPEC: {n - ll_mapped})")
    print(f"  bbox assigned (approx)     : {bbox_assigned}/{n}")
    print(f"  download_url usable         : {url_ok}/{n} (rest nulled)")
    print(f"  contact email extracted    : {email_ok}/{n}")
    print(f"  readiness_status mapped    : {readiness_ok}/{n} from registry value")

    flag_counts = Counter(f for r in records for f in r["flags"])
    print("  flags emitted:")
    for f, c in flag_counts.most_common():
        print(f"      {c:3} | {f}")

    code_counts = Counter(r["living_landscape"] for r in records)
    print("  records per landscape code:")
    for code, c in sorted(code_counts.items()):
        print(f"      {c:3} | {code:12} {vocab.landscape_name(code)}")

    if vocab.added_codes:
        print("  CODES ADDED at runtime (confirm with specialist/Lizeth):")
        for a in vocab.added_codes:
            print(f"      {a['code']} ({a['country']}): {a['reason']}")

    climate = [r["id"] for r in records if r["is_climate_linked"]]
    print(f"  climate-linked items (link to CDH): {len(climate)}")


if __name__ == "__main__":
    raise SystemExit(main())
