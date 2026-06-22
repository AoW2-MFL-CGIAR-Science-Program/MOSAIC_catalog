"""MOSAIC catalog pipeline.

Reads the MFL Dataset Registry (single source of truth) and emits two artifacts:
  A. A static STAC catalog tree (plain JSON, no pystac).
  B. The frontend datasets.json data contract.

MOSAIC is a coordination network and metadata system (not a repository/platform/
database). For climate layers it links to the CGIAR Climate Data Hub (CDH) rather
than re-describing them ("connect, don't duplicate").
"""

__version__ = "0.1.0"
