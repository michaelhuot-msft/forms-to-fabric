"""Tests for the de-identification module."""

import sys
from pathlib import Path

import pytest

# Allow imports from the functions package
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "functions"))

from shared.deid import (  # noqa: E402
    apply_deid,
    generalize_value,
    hash_value,
    redact_value,
)
from shared.models import Answer, FieldConfig  # noqa: E402


class TestHashValue:
    """Tests for hash_value()."""

    def test_consistent_output(self) -> None:
        """Same input must always produce the same hash."""
        assert hash_value("John Doe") == hash_value("John Doe")

    def test_different_inputs_produce_different_hashes(self) -> None:
        assert hash_value("Alice") != hash_value("Bob")

    def test_returns_hex_string(self) -> None:
        result = hash_value("test")
        assert all(c in "0123456789abcdef" for c in result)
        assert len(result) == 64  # SHA-256 hex length


class TestRedactValue:
    """Tests for redact_value()."""

    def test_replaces_with_marker(self) -> None:
        assert redact_value("Sensitive Info") == "[REDACTED]"

    def test_empty_string(self) -> None:
        assert redact_value("") == "[REDACTED]"


class TestGeneralizeValue:
    """Tests for generalize_value()."""

    def test_date_generalization(self) -> None:
        assert generalize_value("2024-01-15", "date") == "2024-01"

    def test_date_iso_format(self) -> None:
        assert generalize_value("1990-12-25T08:00:00Z", "date") == "1990-12"

    def test_age_generalization(self) -> None:
        assert generalize_value("34", "age") == "30-39"

    def test_age_boundary(self) -> None:
        assert generalize_value("40", "age") == "40-49"

    def test_age_zero(self) -> None:
        assert generalize_value("0", "age") == "0-9"

    def test_unknown_field_type(self) -> None:
        assert generalize_value("anything", "unknown") == "[GENERALIZED]"

    def test_no_field_type(self) -> None:
        assert generalize_value("anything", None) == "[GENERALIZED]"

    def test_non_numeric_age(self) -> None:
        """Non-numeric age value should be returned as-is."""
        assert generalize_value("N/A", "age") == "N/A"


class TestApplyDeid:
    """Tests for apply_deid()."""

    def test_phi_fields_are_deidentified(self) -> None:
        answers = [
            Answer(question_id="q1", question="Name", answer="John Doe"),
            Answer(question_id="q2", question="Rating", answer="5"),
        ]
        configs = [
            FieldConfig(
                question_id="q1",
                field_name="patient_name",
                contains_phi=True,
                deid_method="redact",
            ),
            FieldConfig(
                question_id="q2",
                field_name="rating",
                contains_phi=False,
            ),
        ]
        raw, deid = apply_deid(answers, configs)

        assert raw[0]["value"] == "John Doe"
        assert deid[0]["value"] == "[REDACTED]"
        # Non-PHI field unchanged
        assert raw[1]["value"] == "5"
        assert deid[1]["value"] == "5"

    def test_field_names_mapped(self) -> None:
        answers = [Answer(question_id="q1", question="Q", answer="A")]
        configs = [
            FieldConfig(question_id="q1", field_name="mapped_name", contains_phi=False)
        ]
        raw, deid = apply_deid(answers, configs)
        assert raw[0]["field_name"] == "mapped_name"

    def test_unknown_question_id_uses_question_id_as_name(self) -> None:
        answers = [Answer(question_id="qX", question="Q", answer="A")]
        raw, deid = apply_deid(answers, [])
        assert raw[0]["field_name"] == "qX"
