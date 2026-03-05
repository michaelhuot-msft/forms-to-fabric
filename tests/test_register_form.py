"""Tests for the register-form HTTP endpoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "functions"))

from register_form.handler import handle_register_form  # noqa: E402

# ---------------------------------------------------------------------------
# Sample Graph API responses
# ---------------------------------------------------------------------------

SAMPLE_METADATA = {"title": "Cardiology Intake", "description": "Patient intake form"}

SAMPLE_QUESTIONS = [
    {"id": "q1", "title": "Patient Name", "type": "text"},
    {"id": "q2", "title": "Date of Birth", "type": "date"},
    {"id": "q3", "title": "Satisfaction Rating", "type": "rating"},
]

VALID_FORM_URL = "https://forms.office.com/Pages/DesignPageV2.aspx?id=abc123&origin=shell"


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


def _make_registry(tmp_path: Path, forms: list | None = None) -> Path:
    """Create a temporary registry file and return its path."""
    config_dir = tmp_path / "config"
    config_dir.mkdir(exist_ok=True)
    registry_path = config_dir / "form-registry.json"
    registry_path.write_text(
        json.dumps({"forms": forms or []}, indent=2), encoding="utf-8"
    )
    return registry_path


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRegisterForm:
    def test_register_non_phi_form(self, tmp_path: Path) -> None:
        registry_path = _make_registry(tmp_path)

        req = _make_request(
            {"form_url": VALID_FORM_URL, "has_phi": False}
        )

        with (
            patch("register_form.handler._registry_path", return_value=str(registry_path)),
            patch("register_form.handler.get_form_config", return_value=None),
            patch("register_form.handler.GraphClient") as MockGraph,
        ):
            mock_instance = MockGraph.return_value
            mock_instance.get_form_metadata.return_value = SAMPLE_METADATA
            mock_instance.get_form_questions.return_value = SAMPLE_QUESTIONS

            resp = handle_register_form(req)

        assert resp.status_code == 200
        result = json.loads(resp.get_body())
        assert result["form_id"] == "abc123"
        assert result["form_name"] == "Cardiology Intake"
        assert result["target_table"] == "cardiology_intake"
        assert result["status"] == "active"
        assert result["field_count"] == 3

        # Verify registry was updated
        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        assert len(registry["forms"]) == 1
        for field in registry["forms"][0]["fields"]:
            assert field["contains_phi"] is False

    def test_register_phi_form(self, tmp_path: Path) -> None:
        registry_path = _make_registry(tmp_path)

        req = _make_request(
            {"form_url": VALID_FORM_URL, "has_phi": True}
        )

        with (
            patch("register_form.handler._registry_path", return_value=str(registry_path)),
            patch("register_form.handler.get_form_config", return_value=None),
            patch("register_form.handler.GraphClient") as MockGraph,
        ):
            mock_instance = MockGraph.return_value
            mock_instance.get_form_metadata.return_value = SAMPLE_METADATA
            mock_instance.get_form_questions.return_value = SAMPLE_QUESTIONS

            resp = handle_register_form(req)

        assert resp.status_code == 200
        result = json.loads(resp.get_body())
        assert result["status"] == "pending_review"

    def test_duplicate_form_id(self, tmp_path: Path) -> None:
        registry_path = _make_registry(tmp_path)
        existing_config = MagicMock()

        req = _make_request(
            {"form_url": VALID_FORM_URL, "has_phi": False}
        )

        with (
            patch("register_form.handler._registry_path", return_value=str(registry_path)),
            patch("register_form.handler.get_form_config", return_value=existing_config),
        ):
            resp = handle_register_form(req)

        assert resp.status_code == 409
        result = json.loads(resp.get_body())
        assert "already registered" in result["error"]

    def test_missing_form_url(self) -> None:
        req = _make_request({"has_phi": False})
        resp = handle_register_form(req)
        assert resp.status_code == 400
        result = json.loads(resp.get_body())
        assert "form_url" in result["error"]

    def test_invalid_url(self, tmp_path: Path) -> None:
        registry_path = _make_registry(tmp_path)

        req = _make_request(
            {"form_url": "https://example.com/not-a-form", "has_phi": False}
        )

        with patch("register_form.handler._registry_path", return_value=str(registry_path)):
            resp = handle_register_form(req)

        assert resp.status_code == 400
        result = json.loads(resp.get_body())
        assert "Cannot extract form_id" in result["error"]

    def test_graph_api_404(self, tmp_path: Path) -> None:
        from shared.graph_client import FormNotFoundError

        registry_path = _make_registry(tmp_path)

        req = _make_request(
            {"form_url": VALID_FORM_URL, "has_phi": False}
        )

        with (
            patch("register_form.handler._registry_path", return_value=str(registry_path)),
            patch("register_form.handler.get_form_config", return_value=None),
            patch("register_form.handler.GraphClient") as MockGraph,
        ):
            mock_instance = MockGraph.return_value
            mock_instance.get_form_metadata.side_effect = FormNotFoundError("abc123")

            resp = handle_register_form(req)

        assert resp.status_code == 404
        result = json.loads(resp.get_body())
        assert "not found" in result["error"]
