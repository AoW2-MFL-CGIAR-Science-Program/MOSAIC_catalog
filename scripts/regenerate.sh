#!/usr/bin/env bash
# Regenerate the MOSAIC catalog and sync datasets.json into the frontend.
#
# The flow:
#   1. rebuild stac/ + datasets.json from the committed registry snapshot
#   2. copy datasets.json into the sibling frontend repo's data folder
#
# After this runs, commit & push in BOTH repos to publish:
#   - MOSAIC_catalog : git add stac datasets.json && git commit && git push   (publishes the STAC endpoint)
#   - frontend       : git add frontend/data/datasets.json && git commit && git push   (publishes the site)
#
# Requires: python3 with openpyxl. Run from anywhere.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$HERE"

echo "Regenerating MOSAIC catalog from $HERE/catalog/MFL_Dataset_Registry.xlsx ..."
python3 build_catalog.py --sync-frontend

echo
echo "Done. datasets.json rebuilt and synced to the frontend."
echo "Review the diffs, then commit & push each repo to publish."
