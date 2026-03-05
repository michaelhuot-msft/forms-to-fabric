"""De-identification utilities for PHI fields.

All functions are deterministic — the same input always produces the same output.
"""

from __future__ import annotations

import hashlib
import re
from typing import Optional

from .models import Answer, FieldConfig


def hash_value(value: str) -> str:
    """Return a hex-encoded SHA-256 hash of *value*.

    The hash is deterministic: identical inputs always yield the same digest.
    """
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def redact_value(value: str) -> str:
    """Replace *value* with a fixed redaction marker."""
    return "[REDACTED]"


def generalize_value(value: str, field_type: Optional[str] = None) -> str:
    """Generalize *value* based on its semantic *field_type*.

    Supported field types:
    - ``"date"`` — keeps only year-month (e.g. ``"2024-01"``).
    - ``"age"``  — maps to a decade range (e.g. ``"30-39"``).
    - anything else — returns ``"[GENERALIZED]"``.
    """
    if field_type == "date":
        match = re.match(r"(\d{4})-(\d{2})", value)
        if match:
            return f"{match.group(1)}-{match.group(2)}"
        return value

    if field_type == "age":
        try:
            age = int(value)
            decade_start = (age // 10) * 10
            return f"{decade_start}-{decade_start + 9}"
        except ValueError:
            return value

    return "[GENERALIZED]"


def apply_deid(
    answers: list[Answer],
    field_configs: list[FieldConfig],
) -> tuple[list[dict], list[dict]]:
    """Apply de-identification rules to *answers* using *field_configs*.

    Returns a ``(raw_records, deidentified_records)`` tuple.  Both lists
    contain plain dicts suitable for DataFrame construction.  The raw list
    preserves original values; the de-identified list has PHI fields
    transformed according to each field's ``deid_method``.
    """
    config_lookup: dict[str, FieldConfig] = {fc.question_id: fc for fc in field_configs}

    raw_records: list[dict] = []
    deid_records: list[dict] = []

    for ans in answers:
        cfg = config_lookup.get(ans.question_id)
        field_name = cfg.field_name if cfg else ans.question_id

        raw_records.append({"field_name": field_name, "value": ans.answer})

        if cfg and cfg.contains_phi and cfg.deid_method:
            if cfg.deid_method == "hash":
                deid_value = hash_value(ans.answer)
            elif cfg.deid_method == "redact":
                deid_value = redact_value(ans.answer)
            elif cfg.deid_method == "generalize":
                deid_value = generalize_value(ans.answer, cfg.field_type)
            else:
                deid_value = ans.answer
        else:
            deid_value = ans.answer

        deid_records.append({"field_name": field_name, "value": deid_value})

    return raw_records, deid_records
