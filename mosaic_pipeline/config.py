"""Shared pipeline configuration.

STAC_BASE_URL is the canonical public endpoint where the STAC tree is published
(the GitHub Pages site of the MOSAIC_catalog repo). Every absolute `metadata_url`
(consumed by the frontend) and every STAC object `self` link is built from it.

The repo name `MOSAIC_catalog` is FROZEN as an API contract (see
docs/ADR-001-repo-architecture.md): renaming it or changing its case silently
breaks every absolute metadata_url, every STAC self link, and any external
(e.g. CDH) cross-link. If a custom domain is adopted later
(e.g. catalog.mosaic.cgiar.org), change only this constant and regenerate.
"""

STAC_BASE_URL = "https://aow2-mfl-cgiar-science-program.github.io/MOSAIC_catalog/stac"
