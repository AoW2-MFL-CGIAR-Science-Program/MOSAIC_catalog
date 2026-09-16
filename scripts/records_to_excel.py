#!/usr/bin/env python3
"""Regenerate the Excel working view from records/ (records -> Excel).

The inverse of scripts/excel_to_records.py. records/<ID>.yaml is the source of
truth; this script rewrites the " Registry" sheet of
catalog/MFL_Dataset_Registry.xlsx from those records so the workbook stays a
faithful import/working view (and a valid CI fallback). Run it after any edit
under records/:

    python3 scripts/records_to_excel.py

What it does — and the two openpyxl traps it handles (both bit us 2026-09-16):

- Keeps the Instructions and Reference sheets and the header + placeholder rows
  (rows 1-2) untouched; rewrites data rows 3.. from records in ascending-id
  order, copying cell styles from rows 3/4 so banding is preserved.
- `living_landscape` bare codes are written back as the controlled
  "CODE — Name" values taken from Reference!K (never hardcoded here).
- **Hyperlink trap:** setting `cell.value = None` does NOT clear a cell that
  carries a Hyperlink object — openpyxl re-materializes the link text on save.
  Every cleared cell also gets `cell.hyperlink = None`, and stray hyperlink-only
  ghost cells below the data (they made the Excel build invent phantom records)
  are purged.
- **Validation trap:** the original cross-sheet dropdowns are stored as an x14
  extension openpyxl silently drops on save. They are recreated as classic
  DataValidations via workbook defined names pointing at the Reference ranges.
- Verifies after saving: reloads the file and compares every cell against the
  records (exit 1 on any mismatch or ghost row).

The Excel path cannot carry the YAML-only forward fields (citation, doi, ...):
a --from-excel build is byte-identical in stac/ and differs in datasets.json
only where records carry a citation. That gap is by design (see SNAPSHOT_NOTE).
"""
from __future__ import annotations

import sys
import warnings
from copy import copy
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent  # repo root (MOSAIC_catalog/)
sys.path.insert(0, str(HERE))

import openpyxl  # noqa: E402
import yaml  # noqa: E402
from openpyxl.workbook.defined_name import DefinedName  # noqa: E402
from openpyxl.worksheet.datavalidation import DataValidation  # noqa: E402

XLSX = HERE / "catalog" / "MFL_Dataset_Registry.xlsx"
RECORDS_DIR = HERE / "records"
SHEET = " Registry"  # leading space is intentional (matches registry.py)

# YAML key per Excel column, in column order 1..23 (matches registry.py COL).
ORDER = [
    "id", "title", "country", "theme", "living_landscape", "data_type",
    "spatial_resolution", "temporal_coverage", "source", "contact",
    "access_level", "license", "processing_status", "file_names",
    "current_location", "migration_status", "server_path", "description",
    "date_registered", "last_updated", "update_frequency", "download_url",
    "file_size",
]

# Defined name -> (Reference-sheet range, Registry column) for the dropdowns.
VALIDATIONS = {
    "MOSAIC_Countries": ("$A$2:$A$15", 3),
    "MOSAIC_Themes": ("$C$2:$C$14", 4),
    "MOSAIC_LLs": ("$K$2:$K$14", 5),
    "MOSAIC_DataTypes": ("$E$2:$E$6", 6),
    "MOSAIC_Sources": ("$G$2:$G$17", 9),
    "MOSAIC_Access": ("$I$2:$I$4", 11),
    "MOSAIC_Migration": ("$O$2:$O$3", 16),
    "MOSAIC_UpdFreq": ("$Q$2:$Q$7", 21),
}


def load_records() -> list[dict]:
    recs = []
    for p in sorted(RECORDS_DIR.glob("*.yaml")):
        recs.append(yaml.safe_load(p.read_text().split("\n", 1)[1]))
    return recs


def main() -> int:
    recs = load_records()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")  # "Data Validation extension..." on load
        wb = openpyxl.load_workbook(XLSX)
    ws = wb[SHEET]
    ref = wb["Reference"]

    ll_disp = {
        str(ref.cell(r, 11).value).split(" — ")[0].strip(): str(ref.cell(r, 11).value)
        for r in range(2, ref.max_row + 1)
        if ref.cell(r, 11).value and " — " in str(ref.cell(r, 11).value)
    }

    styles = {row: [(copy(ws.cell(row, c)._style), ws.cell(row, c).number_format)
                    for c in range(1, 24)] for row in (3, 4)}

    # Clear values AND hyperlinks (see hyperlink trap above), with margin.
    for r in range(3, max(ws.max_row, 200) + 1):
        for c in range(1, 31):
            cell = ws.cell(r, c)
            cell.value = None
            cell.hyperlink = None
    ws._hyperlinks = [
        h for h in ws._hyperlinks
        if h.ref and int("".join(ch for ch in h.ref if ch.isdigit())) < 3
    ]

    for i, rec in enumerate(recs):
        r = 3 + i
        src = styles[3 if i % 2 == 0 else 4]
        for c, key in enumerate(ORDER, start=1):
            v = rec.get(key)
            if key == "living_landscape":
                v = ll_disp.get(v, v)
            cell = ws.cell(r, c)
            cell.value = v
            cell._style, cell.number_format = copy(src[c - 1][0]), src[c - 1][1]

    # Recreate dropdowns (reset first so reruns don't stack duplicates).
    ws.data_validations.dataValidation = []
    existing = set(wb.defined_names.keys())
    for name, (rng, col) in VALIDATIONS.items():
        if name not in existing:
            wb.defined_names.add(DefinedName(name, attr_text=f"Reference!{rng}"))
        dv = DataValidation(type="list", formula1=f"={name}", allow_blank=True)
        letter = ws.cell(3, col).column_letter
        dv.add(f"{letter}3:{letter}200")
        ws.add_data_validation(dv)

    wb.save(XLSX)

    # Verify: reload and compare every cell; scan for ghost rows below the data.
    wb2 = openpyxl.load_workbook(XLSX, data_only=True)
    ws2 = wb2[SHEET]
    errs = 0
    for i, rec in enumerate(recs):
        r = 3 + i
        for c, key in enumerate(ORDER, start=1):
            want = rec.get(key)
            if key == "living_landscape":
                want = ll_disp.get(want, want)
            got = ws2.cell(r, c).value
            if (want or None) != (got or None):
                errs += 1
                print(f"MISMATCH row {r} {key}: want={want!r} got={got!r}")
    for r in range(3 + len(recs), ws2.max_row + 1):
        for c in range(1, 31):
            if ws2.cell(r, c).value not in (None, ""):
                errs += 1
                print(f"GHOST row {r} col {c}: {ws2.cell(r, c).value!r}")
    if errs:
        print(f"FAILED: {errs} mismatch(es) — do not commit this workbook.")
        return 1
    print(f"OK: {len(recs)} records written to {XLSX.name} and verified.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
