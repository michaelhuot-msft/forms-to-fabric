"""Tests for scripts/manage_registry.py."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

# Import the CLI module
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import manage_registry as cli


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

VALID_REGISTRY = {
    "forms": [
        {
            "form_id": "test-form-001",
            "form_name": "Test Form",
            "target_table": "test_table",
            "status": "active",
            "fields": [
                {
                    "question_id": "q1",
                    "field_name": "name",
                    "contains_phi": True,
                    "deid_method": "hash",
                    "field_type": None,
                },
                {
                    "question_id": "q2",
                    "field_name": "score",
                    "contains_phi": False,
                    "deid_method": None,
                    "field_type": None,
                },
            ],
        }
    ]
}


@pytest.fixture()
def registry_dir(tmp_path: Path) -> Path:
    """Create a temporary directory with a valid registry and schema."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()

    registry_path = config_dir / "form-registry.json"
    registry_path.write_text(json.dumps(VALID_REGISTRY, indent=2), encoding="utf-8")

    # Copy schema from repo
    schema_src = Path(__file__).resolve().parent.parent / "config" / "form-registry.schema.json"
    schema_dst = config_dir / "form-registry.schema.json"
    schema_dst.write_text(schema_src.read_text(encoding="utf-8"), encoding="utf-8")

    return tmp_path


def registry_path(base: Path) -> Path:
    return base / "config" / "form-registry.json"


def schema_path(base: Path) -> Path:
    return base / "config" / "form-registry.schema.json"


def run_cli(base: Path, argv: list[str]) -> int:
    """Run the CLI with --registry and --schema pointed at the temp dir."""
    full_argv = [
        "--registry", str(registry_path(base)),
        "--schema", str(schema_path(base)),
        *argv,
    ]
    return cli.main(full_argv)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestValidate:
    def test_validate_valid_registry(self, registry_dir: Path) -> None:
        rc = run_cli(registry_dir, ["validate"])
        assert rc == 0

    def test_validate_invalid_json(self, registry_dir: Path) -> None:
        rp = registry_path(registry_dir)
        rp.write_text("{bad json", encoding="utf-8")
        rc = run_cli(registry_dir, ["validate"])
        assert rc == 1

    def test_validate_duplicate_form_id(self, registry_dir: Path) -> None:
        rp = registry_path(registry_dir)
        data = json.loads(rp.read_text(encoding="utf-8"))
        # Add a duplicate form
        dup = data["forms"][0].copy()
        data["forms"].append(dup)
        rp.write_text(json.dumps(data, indent=2), encoding="utf-8")

        rc = run_cli(registry_dir, ["validate"])
        assert rc == 1


class TestAddForm:
    def test_add_form_with_id(self, registry_dir: Path) -> None:
        rc = run_cli(registry_dir, [
            "add-form",
            "--form-id", "new-form-002",
            "--form-name", "New Form",
            "--target-table", "new_table",
        ])
        assert rc == 0

        data = json.loads(registry_path(registry_dir).read_text(encoding="utf-8"))
        ids = [f["form_id"] for f in data["forms"]]
        assert "new-form-002" in ids

        # New form should have empty fields list
        new_form = [f for f in data["forms"] if f["form_id"] == "new-form-002"][0]
        assert new_form["fields"] == []

    def test_add_form_with_url(self, registry_dir: Path) -> None:
        rc = run_cli(registry_dir, [
            "add-form",
            "--form-url", "https://forms.office.com/Pages/DesignPageV2.aspx?id=url-form-003&origin=lprLink",
            "--target-table", "url_table",
        ])
        assert rc == 0

        data = json.loads(registry_path(registry_dir).read_text(encoding="utf-8"))
        new_form = [f for f in data["forms"] if f["form_id"] == "url-form-003"][0]
        assert new_form["target_table"] == "url_table"
        # form_name defaults to form_id when Graph API is unavailable
        assert new_form["form_name"] == "url-form-003"

    def test_add_form_url_only(self, registry_dir: Path) -> None:
        """Just a URL — target_table and form_name are both derived."""
        rc = run_cli(registry_dir, [
            "add-form",
            "--form-url", "https://forms.office.com/Pages/DesignPageV2.aspx?id=minimal-form-004",
        ])
        assert rc == 0

        data = json.loads(registry_path(registry_dir).read_text(encoding="utf-8"))
        new_form = [f for f in data["forms"] if f["form_id"] == "minimal-form-004"][0]
        # Both derived from form_id since Graph API is unavailable
        assert new_form["form_name"] == "minimal-form-004"
        assert new_form["target_table"] == "minimal_form_004"

    def test_add_form_bad_url(self, registry_dir: Path) -> None:
        rc = run_cli(registry_dir, [
            "add-form",
            "--form-url", "https://example.com/not-a-form",
            "--target-table", "bad_table",
        ])
        assert rc == 1

    def test_add_form_duplicate(self, registry_dir: Path) -> None:
        rc = run_cli(registry_dir, [
            "add-form",
            "--form-id", "test-form-001",
            "--form-name", "Duplicate",
            "--target-table", "dup_table",
        ])
        assert rc == 1


class TestAddField:
    def test_add_field(self, registry_dir: Path) -> None:
        rc = run_cli(registry_dir, [
            "add-field",
            "--form-id", "test-form-001",
            "--question-id", "q3",
            "--field-name", "new_field",
            "--deid-method", "none",
        ])
        assert rc == 0

        data = json.loads(registry_path(registry_dir).read_text(encoding="utf-8"))
        form = [f for f in data["forms"] if f["form_id"] == "test-form-001"][0]
        qids = [f["question_id"] for f in form["fields"]]
        assert "q3" in qids

    def test_add_field_phi_requires_deid(self, registry_dir: Path) -> None:
        rc = run_cli(registry_dir, [
            "add-field",
            "--form-id", "test-form-001",
            "--question-id", "q_phi",
            "--field-name", "phi_field",
            "--contains-phi",
            "--deid-method", "none",
        ])
        assert rc == 1

    def test_add_field_with_phi_and_deid(self, registry_dir: Path) -> None:
        rc = run_cli(registry_dir, [
            "add-field",
            "--form-id", "test-form-001",
            "--question-id", "q_phi",
            "--field-name", "phi_field",
            "--contains-phi",
            "--deid-method", "redact",
        ])
        assert rc == 0

    def test_add_field_nonexistent_form(self, registry_dir: Path) -> None:
        rc = run_cli(registry_dir, [
            "add-field",
            "--form-id", "no-such-form",
            "--question-id", "q1",
            "--field-name", "field",
        ])
        assert rc == 1

    def test_add_field_duplicate_question_id(self, registry_dir: Path) -> None:
        rc = run_cli(registry_dir, [
            "add-field",
            "--form-id", "test-form-001",
            "--question-id", "q1",
            "--field-name", "duplicate_field",
        ])
        assert rc == 1


class TestListForms:
    def test_list_forms(self, registry_dir: Path, capsys: pytest.CaptureFixture[str]) -> None:
        rc = run_cli(registry_dir, ["list"])
        assert rc == 0

        output = capsys.readouterr().out
        assert "test-form-001" in output
        assert "Test Form" in output
        assert "test_table" in output
        # Should show field count of 2
        lines = output.strip().split("\n")
        data_line = [l for l in lines if "test-form-001" in l][0]
        # 2 fields total, 1 PHI field
        assert "2" in data_line
        assert "1" in data_line


class TestRemoveForm:
    def test_remove_form(self, registry_dir: Path) -> None:
        rc = run_cli(registry_dir, [
            "remove-form",
            "--form-id", "test-form-001",
            "--yes",
        ])
        assert rc == 0

        data = json.loads(registry_path(registry_dir).read_text(encoding="utf-8"))
        ids = [f["form_id"] for f in data["forms"]]
        assert "test-form-001" not in ids

    def test_remove_form_nonexistent(self, registry_dir: Path) -> None:
        rc = run_cli(registry_dir, [
            "remove-form",
            "--form-id", "no-such-form",
            "--yes",
        ])
        assert rc == 1
