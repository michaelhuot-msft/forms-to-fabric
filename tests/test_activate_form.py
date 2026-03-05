"""Tests for the activate-form HTTP endpoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "functions"))

from activate_form.handler import handle_activate_form  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_request(body: dict | None = None) -> MagicMock:
    req = MagicMock()
    if body is not None:
        req.get_json.return_value = body
    else:
        req.get_json.side_effect = ValueError("no body")
    return req


def _make_registry(tmp_path: Path, forms: list) -> Path:
    """Create a temporary registry file and return its path."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    registry_path = config_dir / "form-registry.json"
    registry_path.write_text(json.dumps({"forms": forms}, indent=2), encoding="utf-8")
    return registry_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestActivateForm:
    def test_activate_pending_form(self, tmp_path: Path) -> None:
        forms = [
            {
                "form_id": "test-123",
                "form_name": "Test Form",
                "target_table": "test_form",
                "status": "pending_review",
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
        registry_path = _make_registry(tmp_path, forms)
        req = _make_request({"form_id": "test-123"})

        with (
            patch(
                "activate_form.handler._registry_path", return_value=str(registry_path)
            ),
            patch("activate_form.handler.invalidate_cache"),
        ):
            resp = handle_activate_form(req)

        assert resp.status_code == 200
        result = json.loads(resp.get_body())
        assert result["status"] == "active"
        assert result["form_id"] == "test-123"
        assert (
            "activated" in result["message"].lower()
            or "active" in result["message"].lower()
        )

        # Verify registry was updated on disk
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        assert registry["forms"][0]["status"] == "active"

    def test_activate_already_active(self, tmp_path: Path) -> None:
        forms = [
            {
                "form_id": "test-123",
                "form_name": "Test Form",
                "target_table": "test_form",
                "status": "active",
                "fields": [],
            }
        ]
        registry_path = _make_registry(tmp_path, forms)
        req = _make_request({"form_id": "test-123"})

        with patch(
            "activate_form.handler._registry_path", return_value=str(registry_path)
        ):
            resp = handle_activate_form(req)

        assert resp.status_code == 200
        result = json.loads(resp.get_body())
        assert result["message"] == "already active"

    def test_activate_with_unconfigured_phi(self, tmp_path: Path) -> None:
        forms = [
            {
                "form_id": "test-123",
                "form_name": "Test Form",
                "target_table": "test_form",
                "status": "pending_review",
                "fields": [
                    {
                        "question_id": "q1",
                        "field_name": "patient_name",
                        "contains_phi": True,
                        "deid_method": None,
                        "field_type": None,
                    },
                    {
                        "question_id": "q2",
                        "field_name": "dob",
                        "contains_phi": True,
                        "deid_method": "hash",
                        "field_type": None,
                    },
                    {
                        "question_id": "q3",
                        "field_name": "score",
                        "contains_phi": False,
                        "deid_method": None,
                        "field_type": None,
                    },
                ],
            }
        ]
        registry_path = _make_registry(tmp_path, forms)
        req = _make_request({"form_id": "test-123"})

        with patch(
            "activate_form.handler._registry_path", return_value=str(registry_path)
        ):
            resp = handle_activate_form(req)

        assert resp.status_code == 400
        result = json.loads(resp.get_body())
        assert "unconfigured_fields" in result
        assert "patient_name" in result["unconfigured_fields"]
        assert "dob" not in result["unconfigured_fields"]

    def test_missing_form_id(self) -> None:
        req = _make_request({})
        resp = handle_activate_form(req)
        assert resp.status_code == 400
        result = json.loads(resp.get_body())
        assert "form_id" in result["error"]

    def test_form_not_found(self, tmp_path: Path) -> None:
        registry_path = _make_registry(tmp_path, [])
        req = _make_request({"form_id": "nonexistent"})

        with patch(
            "activate_form.handler._registry_path", return_value=str(registry_path)
        ):
            resp = handle_activate_form(req)

        assert resp.status_code == 404
        result = json.loads(resp.get_body())
        assert "not found" in result["error"]
