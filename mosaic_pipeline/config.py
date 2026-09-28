"""Shared pipeline configuration.

STAC_BASE_URL is the canonical public endpoint where the STAC tree is published
(the GitHub Pages site of the MOSAIC-mfl/catalog repo). Every absolute `metadata_url`
(consumed by the frontend) and every STAC object `self` link is built from it.

The org handle `MOSAIC-mfl` and the repo name `catalog` are the API contract
(see docs/ADR-001-repo-architecture.md): renaming either, or changing the repo
name's case, silently breaks every absolute metadata_url, every STAC self link,
and any external (e.g. CDH) cross-link. They were renamed once, on 2026-09-28
(from AoW2-MFL-CGIAR-Science-Program/MOSAIC_catalog). If a custom domain is
adopted later (e.g. catalog.mosaic.cgiar.org), change only this constant and
regenerate.
"""

STAC_BASE_URL = "https://mosaic-mfl.github.io/catalog/stac"
