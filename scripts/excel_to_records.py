#!/usr/bin/env python3
"""One-time migration: Excel registry -> records/<ID>.yaml (source-of-truth flip).

Reads catalog/MFL_Dataset_Registry.xlsx EXACTLY as mosaic_pipeline/registry.py
does (same ' Registry' sheet, same empty-row and placeholder-row skip) and writes
one YAML file per record. Rules that make the flip byte-identical downstream:

- Every field is stored as the exact post-T.s() string the Excel path produces
  (datetime/int cells serialize through T.s at migration time; T.s is idempotent,
  so re-normalizing the YAML value later is a no-op).
- `living_landscape` stores the BARE canonical code parsed from the controlled
  "CODE — Name" value (NATIONAL/GLOBAL likewise bare).
- `file_size` keeps the raw cell scalar (int stays int, '220 MB' stays a string).
- Two normalizations that the Excel path already performs are baked in (and
  reported as migration warnings) so the files pass the schema enums:
    * data_type 'Soil dataset' -> null   (registry.py nulls it too)
    * access_level 'CGIAR-internal'/'CGIAR internal' -> 'Internal' (ACCESS_ALIASES)
  Any OTHER out-of-enum value is kept verbatim and reported — the subsequent
  build will fail validation, forcing a human decision instead of silent loss.
- Dumped with yaml.safe_dump(allow_unicode=True, sort_keys=False, width=100);
  every file is re-loaded and compared value-by-value (and type-by-type) to
  verify PyYAML's automatic quoting round-trips byte-identically.

Usage:  python3 scripts/excel_to_records.py [--force]
        (--force overwrites an existing non-empty records/ directory)
"""
from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # repo root (MOSAIC_catalog/)
sys.path.insert(0, str(HERE))

import openpyxl  # noqa: E402
import yaml  # noqa: E402

from mosaic_pipeline import transform as T  # noqa: E402
from mosaic_pipeline.records import load_schema, record_key_order  # noqa: E402
from mosaic_pipeline.registry import (  # noqa: E402
    ACCESS_ALIASES, COL, SHEET_NAME, _g,
)

REGISTRY_XLSX = HERE / "catalog" / "MFL_Dataset_Registry.xlsx"
RECORDS_DIR = HERE / "records"

# YAML key -> how to pull it from the row. Everything not listed here is the
# plain post-T.s() of the same-named COL field.
CORE_KEYS_SPECIAL = {"id", "living_landscape", "data_type", "access_level",
                     "temporal_coverage", "file_size"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--force", action="store_true",
                        help="overwrite an existing non-empty records/ directory")
    args = parser.parse_args(argv)

    schema = load_schema()
    key_order = record_key_order(schema)
    core_keys = [k for k in key_order
                 if k not in ("encoding", "bbox", "crs", "citation", "doi",
                              "keywords", "media_type")]
    enums = {k: v["enum"] for k, v in schema["properties"].items() if "enum" in v}

    existing = sorted(RECORDS_DIR.glob("*.yaml")) if RECORDS_DIR.is_dir() else []
    if existing and not args.force:
        print(f"ERROR: {RECORDS_DIR} already holds {len(existing)} .yaml file(s). "
              f"This is a one-time migration; re-run with --force to overwrite.")
        return 1

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # silence "Data Validation extension..."
        wb = openpyxl.load_workbook(REGISTRY_XLSX, data_only=True)
    ws = wb[SHEET_NAME]

    fatals: list[str] = []
    warns: list[str] = []
    records: list[dict] = []

    for i, row in enumerate(ws.iter_rows(min_row=2, values_only=True), start=2):
        if all(T.s(c) is None for c in row):
            continue
        if T.is_placeholder_row(row):
            continue

        rid = T.s(_g(row, "record_id"))
        if not rid:
            fatals.append(f"row {i}: missing Record ID — the records/ model requires "
                          f"literal ids; fix the Excel first")
            continue

        rec: dict = {}
        for key in core_keys:
            if key == "id":
                rec["id"] = rid
            elif key == "living_landscape":
                raw = T.s(_g(row, "living_landscape"))
                code = raw.split("—")[0].strip() if raw else None
                if code not in enums["living_landscape"]:
                    fatals.append(f"{rid} (row {i}): living landscape {raw!r} does not "
                                  f"start with a canonical code — normalize the Excel "
                                  f"value first")
                rec["living_landscape"] = code
            elif key == "data_type":
                val = T.s(_g(row, "data_type"))
                if val == "Soil dataset":
                    warns.append(f"{rid}: data_type 'Soil dataset' -> null (registry.py "
                                 f"nulls it; not a data type — needs upstream fix)")
                    val = None
                elif val not in enums["data_type"]:
                    warns.append(f"{rid}: data_type {val!r} is outside the enum — kept "
                                 f"verbatim; the build WILL fail until it is resolved")
                rec["data_type"] = val
            elif key == "access_level":
                raw = T.s(_g(row, "access_level"))
                val = ACCESS_ALIASES.get(raw, raw)
                if val != raw:
                    warns.append(f"{rid}: access_level {raw!r} -> {val!r} (ACCESS_ALIASES)")
                if val is not None and val not in enums["access_level"]:
                    warns.append(f"{rid}: access_level {val!r} is outside the enum — kept "
                                 f"verbatim; the build WILL fail until it is resolved")
                rec["access_level"] = val
            elif key == "temporal_coverage":
                rec["temporal_coverage"] = T.s(_g(row, "temporal"))
            elif key == "file_size":
                rec["file_size"] = _g(row, "file_size")  # raw scalar, NOT T.s
            else:
                val = T.s(_g(row, key))
                if key in enums and val is not None and val not in enums[key]:
                    warns.append(f"{rid}: {key} {val!r} is outside the enum — kept "
                                 f"verbatim; the build WILL fail until it is resolved")
                rec[key] = val
        records.append(rec)

    dupes = {r["id"] for r in records if sum(x["id"] == r["id"] for x in records) > 1}
    for d in sorted(dupes):
        fatals.append(f"duplicate Record ID in the Excel: {d} — records/ needs unique ids")

    if fatals:
        print(f"MIGRATION ABORTED — {len(fatals)} fatal issue(s), nothing written:")
        for m in fatals:
            print("  -", m)
        return 1

    RECORDS_DIR.mkdir(exist_ok=True)
    roundtrip_fail = 0
    for rec in records:
        path = RECORDS_DIR / f"{rec['id']}.yaml"
        body = yaml.safe_dump(rec, allow_unicode=True, sort_keys=False, width=100)
        text = ("# MOSAIC dataset record — schema: spec/record_schema.md "
                "(the build fails on invalid records)\n" + body)
        path.write_text(text, encoding="utf-8")

        # Round-trip verification: every value AND its type must survive.
        loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
        problems = []
        if list(loaded.keys()) != list(rec.keys()):
            problems.append("key order changed")
        for k in rec:
            if k not in loaded or loaded[k] != rec[k] or type(loaded[k]) is not type(rec[k]):
                problems.append(f"{k}: {rec[k]!r} -> {loaded.get(k)!r}")
        if problems:
            roundtrip_fail += 1
            print(f"ROUND-TRIP FAILURE {path.name}: " + "; ".join(problems))

    print(f"Wrote {len(records)} records to {RECORDS_DIR}")
    print(f"Round-trip verification: {len(records) - roundtrip_fail}/{len(records)} "
          f"files load back value- and type-identical")
    if warns:
        print(f"Migration warnings ({len(warns)}):")
        for m in warns:
            print("  -", m)
    else:
        print("Migration warnings: none")
    return 0 if roundtrip_fail == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
