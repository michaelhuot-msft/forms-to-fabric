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


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestRegisterForm:
    def test_register_non_phi_form(self) -> None:
        mock_save = MagicMock()
        req = _make_request({"form_url": VALID_FORM_URL, "has_phi": False})

        with (
            patch(
                "register_form.handler.load_registry_data",
                return_value={"forms": []},
            ),
            patch("register_form.handler.save_registry_data", mock_save),
            patch("register_form.handler.get_form_config", return_value=None),
        ):
            resp = handle_register_form(req)

        assert resp.status_code == 200
        result = json.loads(resp.get_body())
        assert result["form_id"] == "abc123"
        assert result["status"] == "active"
        assert result["field_count"] == 0  # No Graph API, fields added later

        mock_save.assert_called_once()
        saved = mock_save.call_args[0][0]
        assert len(saved["forms"]) == 1

    def test_register_phi_form(self) -> None:
        mock_save = MagicMock()
        req = _make_request({"form_url": VALID_FORM_URL, "has_phi": True})

        with (
            patch(
                "register_form.handler.load_registry_data",
                return_value={"forms": []},
            ),
            patch("register_form.handler.save_registry_data", mock_save),
            patch("register_form.handler.get_form_config", return_value=None),
        ):
            resp = handle_register_form(req)

        assert resp.status_code == 200
        result = json.loads(resp.get_body())
        assert result["status"] == "pending_review"

    def test_duplicate_form_id(self) -> None:
        existing_config = MagicMock()
        existing_config.form_name = "Existing Form"
        existing_config.target_table = "existing_form"
        req = _make_request({"form_url": VALID_FORM_URL, "has_phi": False})

        with (
            patch(
                "register_form.handler.load_registry_data",
                return_value={"forms": []},
            ),
            patch("register_form.handler.save_registry_data", MagicMock()),
            patch(
                "register_form.handler.get_form_config", return_value=existing_config
            ),
        ):
            resp = handle_register_form(req)

        assert resp.status_code == 200
        result = json.loads(resp.get_body())
        assert result["status"] == "already_registered"

    def test_missing_form_url(self) -> None:
        req = _make_request({"has_phi": False})
        resp = handle_register_form(req)
        assert resp.status_code == 400

    def test_invalid_url(self) -> None:
        req = _make_request(
            {"form_url": "https://example.com/not-a-form", "has_phi": False}
        )
        resp = handle_register_form(req)
        assert resp.status_code == 400

    def test_register_with_has_phi_yes_string(self) -> None:
        """has_phi accepts 'Yes' string from Power Automate."""
        mock_save = MagicMock()
        req = _make_request({"form_url": VALID_FORM_URL, "has_phi": "Yes"})

        with (
            patch(
                "register_form.handler.load_registry_data",
                return_value={"forms": []},
            ),
            patch("register_form.handler.save_registry_data", mock_save),
            patch("register_form.handler.get_form_config", return_value=None),
        ):
            resp = handle_register_form(req)

        assert resp.status_code == 200
        result = json.loads(resp.get_body())
        assert result["status"] == "pending_review"
