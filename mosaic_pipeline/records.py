"""Load + validate the one-YAML-file-per-dataset records (records/<ID>.yaml).

This is the SOURCE-OF-TRUTH path since 2026-07-24 (the Excel registry stays as a
frozen snapshot / CI fallback while the workflow can't install PyYAML). Design:

- Validation is pure python against spec/record_schema.json — a jsonschema-SHAPED
  spec consumed by our own interpreter below (jsonschema is NOT installed; npm is
  blocked). Only the constructs the spec actually uses are implemented: type
  (incl. unions), enum (null in the list = nullable), pattern, minLength,
  required, additionalProperties:false, one level of nested properties (bbox),
  items.type. Keep the spec within that subset.
- Any validation problem is a HARD error: read_records raises
  RecordValidationError carrying the full error list, and build_catalog.py exits
  nonzero listing them. A metadata catalog that half-builds silently is worse
  than one that fails loudly.
- Normalization is SHARED with the Excel path: each YAML record is mapped to the
  same field-dict shape and pushed through registry.normalize_fields(), so both
  sources produce byte-identical artifacts (acceptance-tested 2026-07-24).
  Records are stored as the exact post-T.s() strings the Excel path produced at
  migration time; T.s() is idempotent, so re-normalizing them is a no-op.
- The forward-looking keys (encoding, bbox, crs, citation, doi, keywords,
  media_type) are validated but NOT consumed yet (assessment §4 Phase 1); wiring
  them into the STAC items is a deliberate later step, not a silent side effect.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

from . import transform as T
from .registry import normalize_fields
from .vocab import Vocab

SPEC_DIR = Path(__file__).resolve().parent.parent / "spec"
SCHEMA_PATH = SPEC_DIR / "record_schema.json"

# normalize_fields field-dict key (COL short name) -> YAML key. Keys not listed
# map to themselves. The forward-looking keys are validated but not (yet) fed in.
_FIELD_TO_YAML = {"record_id": "id", "temporal": "temporal_coverage"}
FORWARD_KEYS = ("encoding", "bbox", "crs", "citation", "doi", "keywords", "media_type")


class RecordValidationError(Exception):
    """Raised by read_records; .errors is the full list of human-readable errors."""

    def __init__(self, errors: list[str]):
        super().__init__(f"{len(errors)} record validation error(s)")
        self.errors = errors


def load_schema() -> dict:
    with open(SCHEMA_PATH, encoding="utf-8") as f:
        return json.load(f)


def record_key_order(schema: dict | None = None) -> list[str]:
    """Canonical YAML key order = property order in record_schema.json."""
    schema = schema or load_schema()
    return list(schema["properties"].keys())


# --- pure-python mini-validator (the subset record_schema.json uses) ----------

_TYPE_CHECKS = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "null": lambda v: v is None,
}


def _type_name(v) -> str:
    for name, check in _TYPE_CHECKS.items():
        if name != "number" and check(v):
            return name
    return type(v).__name__


def _check_value(value, spec: dict, where: str) -> list[str]:
    """Validate one value against one property spec. Returns error strings."""
    errs: list[str] = []

    if "enum" in spec:
        if value not in spec["enum"]:
            allowed = ", ".join(repr(x) for x in spec["enum"] if x is not None)
            nullable = " (or null)" if None in spec["enum"] else ""
            errs.append(f"{where}: {value!r} is not an allowed value; expected one of "
                        f"[{allowed}]{nullable}")
        return errs  # enum fully constrains the value

    types = spec.get("type")
    if types is not None:
        tlist = types if isinstance(types, list) else [types]
        if not any(_TYPE_CHECKS[t](value) for t in tlist):
            # The common real cause: an unquoted year/date that YAML turned into
            # an int/date where a string was wanted. Only hint in that case.
            hint = ""
            if "string" in tlist and not isinstance(value, str):
                hint = " — quote year/date values so YAML keeps them strings"
            errs.append(f"{where}: expected {' | '.join(tlist)}, got "
                        f"{_type_name(value)} ({value!r}){hint}")
            return errs

    if value is None:
        return errs

    if "pattern" in spec and isinstance(value, str):
        if not re.search(spec["pattern"], value):
            errs.append(f"{where}: {value!r} does not match pattern {spec['pattern']}")
    if "minLength" in spec and isinstance(value, str):
        if len(value) < spec["minLength"]:
            errs.append(f"{where}: must be at least {spec['minLength']} character(s)")
    if isinstance(value, dict):
        errs += _check_object(value, spec, where)
    if isinstance(value, list) and "items" in spec:
        for i, item in enumerate(value):
            errs += _check_value(item, spec["items"], f"{where}[{i}]")
    return errs


def _check_object(obj: dict, spec: dict, where: str) -> list[str]:
    errs: list[str] = []
    props = spec.get("properties", {})
    if spec.get("additionalProperties") is False:
        unknown = [k for k in obj if k not in props]
        if unknown:
            errs.append(f"{where}: unknown key(s) {', '.join(sorted(map(repr, unknown)))} "
                        f"— not in the schema; see spec/record_schema.md")
    for req in spec.get("required", []):
        if req not in obj or obj.get(req) is None:
            # top-level: required fields must be present AND non-null.
            errs.append(f"{where}: required key '{req}' is missing or null")
    for k, v in obj.items():
        if k in props:
            errs += _check_value(v, props[k], f"{where}.{k}")
    return errs


def validate_record(data, fname: str, schema: dict) -> list[str]:
    """Schema validation of one parsed YAML document (no cross-file checks)."""
    if not isinstance(data, dict):
        return [f"{fname}: top level must be a mapping (got {_type_name(data)})"]
    errs = _check_object(data, schema, fname)
    # Extra: a whitespace-only title passes minLength but is still useless.
    title = data.get("title")
    if isinstance(title, str) and not title.strip():
        errs.append(f"{fname}: title must not be blank")
    return errs


# --- loading -------------------------------------------------------------------

def _fail_gen() -> str:
    raise RuntimeError("id generation must never happen on the records path "
                       "(ids are required and validated)")


def _yaml_to_fields(data: dict) -> dict:
    """YAML record -> the field-dict shape normalize_fields expects."""
    from .registry import COL
    return {col_key: data.get(_FIELD_TO_YAML.get(col_key, col_key)) for col_key in COL}


def read_records(records_dir, vocab: Vocab) -> list[dict]:
    """Read records/<ID>.yaml -> the SAME normalized record dicts the Excel path
    yields (registry.normalize_fields). Raises RecordValidationError on any
    problem; the caller must treat that as a failed build (nonzero exit)."""
    records_dir = Path(records_dir)
    schema = load_schema()
    errors: list[str] = []

    stray = sorted(records_dir.glob("*.yml"))
    for fp in stray:
        errors.append(f"{fp.name}: use the .yaml extension (found .yml — it would be "
                      f"silently skipped otherwise)")

    files = sorted(records_dir.glob("*.yaml"))
    if not files:
        errors.append(f"{records_dir}: no *.yaml records found — refusing to build an "
                      f"empty catalog (use --from-excel if this is intentional)")

    parsed: list[tuple[str, dict]] = []
    ids_seen: dict[str, str] = {}  # id -> first filename
    for fp in files:
        try:
            with open(fp, encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"{fp.name}: YAML parse error: {e}")
            continue

        errs = validate_record(data, fp.name, schema)
        errors += errs
        if not isinstance(data, dict):
            continue

        rid = data.get("id")
        if isinstance(rid, str):
            if fp.stem != rid:
                errors.append(f"{fp.name}: filename does not match id ({rid!r} — "
                              f"expected {rid}.yaml)")
            if rid in ids_seen:
                errors.append(f"{fp.name}: duplicate id {rid!r} (already used by "
                              f"{ids_seen[rid]})")
            else:
                ids_seen[rid] = fp.name
        if not errs:
            parsed.append((fp.name, data))

    if errors:
        raise RecordValidationError(errors)

    used_ids: set[str] = set()
    out: list[dict] = []
    for _fname, data in parsed:
        rec = normalize_fields(_yaml_to_fields(data), vocab, used_ids, _fail_gen)
        rec.pop("_used_seq", None)
        used_ids.add(rec["id"])
        # citation is YAML-only (not in the Excel path's 23 columns) and stays
        # OUT of normalize_fields to preserve Excel/YAML byte-identical output
        # for every field normalize_fields DOES share. Passed through here,
        # raw, as a depositor-supplied preferred citation string (frontend
        # displays it verbatim in place of the auto-generated one when present).
        rec["citation"] = data.get("citation")
        out.append(rec)
    return out
