"""Tests for the register-form HTTP endpoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "functions"))

from register_form.handler import handle_register_form  # noqa: E402

VALID_FORM_URL = (
    "https://forms.office.com/Pages/DesignPageV2.aspx?id=abc123&origin=shell"
)


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
        req = _make_request({"form_url": VALID_FORM_URL, "has_phi": False})

        with (
            patch(
                "register_form.handler._registry_path", return_value=str(registry_path)
            ),
            patch("register_form.handler.get_form_config", return_value=None),
        ):
            resp = handle_register_form(req)

        assert resp.status_code == 200
        result = json.loads(resp.get_body())
        assert result["form_id"] == "abc123"
        assert result["status"] == "active"
        assert result["field_count"] == 0  # No Graph API, fields added later

        registry = json.loads(registry_path.read_text(encoding="utf-8"))
        assert len(registry["forms"]) == 1

    def test_register_phi_form(self, tmp_path: Path) -> None:
        registry_path = _make_registry(tmp_path)
        req = _make_request({"form_url": VALID_FORM_URL, "has_phi": True})

        with (
            patch(
                "register_form.handler._registry_path", return_value=str(registry_path)
            ),
            patch("register_form.handler.get_form_config", return_value=None),
        ):
            resp = handle_register_form(req)

        assert resp.status_code == 200
        result = json.loads(resp.get_body())
        assert result["status"] == "pending_review"

    def test_duplicate_form_id(self, tmp_path: Path) -> None:
        registry_path = _make_registry(tmp_path)
        existing_config = MagicMock()
        req = _make_request({"form_url": VALID_FORM_URL, "has_phi": False})

        with (
            patch(
                "register_form.handler._registry_path", return_value=str(registry_path)
            ),
            patch(
                "register_form.handler.get_form_config", return_value=existing_config
            ),
        ):
            resp = handle_register_form(req)

        assert resp.status_code == 409

    def test_missing_form_url(self) -> None:
        req = _make_request({"has_phi": False})
        resp = handle_register_form(req)
        assert resp.status_code == 400

    def test_invalid_url(self, tmp_path: Path) -> None:
        registry_path = _make_registry(tmp_path)
        req = _make_request(
            {"form_url": "https://example.com/not-a-form", "has_phi": False}
        )

        with patch(
            "register_form.handler._registry_path", return_value=str(registry_path)
        ):
            resp = handle_register_form(req)

        assert resp.status_code == 400

    def test_register_with_has_phi_yes_string(self, tmp_path: Path) -> None:
        """has_phi accepts 'Yes' string from Power Automate."""
        registry_path = _make_registry(tmp_path)
        req = _make_request({"form_url": VALID_FORM_URL, "has_phi": "Yes"})

        with (
            patch(
                "register_form.handler._registry_path", return_value=str(registry_path)
            ),
            patch("register_form.handler.get_form_config", return_value=None),
        ):
            resp = handle_register_form(req)

        assert resp.status_code == 200
        result = json.loads(resp.get_body())
        assert result["status"] == "pending_review"
