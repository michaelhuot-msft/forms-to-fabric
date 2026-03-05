"""Tests for scripts/rotate_function_key.py."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

from scripts.rotate_function_key import rotate


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _mock_credential():
    return MagicMock(name="DefaultAzureCredential")


def _mock_host_keys(existing: dict[str, str] | None = None):
    keys = MagicMock()
    keys.function_keys = existing or {}
    return keys


SUB_ID = "00000000-0000-0000-0000-000000000000"


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestDryRun:
    """--dry-run must not create keys or secrets."""

    @patch("scripts.rotate_function_key.SecretClient")
    @patch("scripts.rotate_function_key.WebSiteManagementClient")
    def test_dry_run_does_not_modify(self, mock_web_cls, mock_secret_cls):
        mock_web = mock_web_cls.return_value
        mock_web.web_apps.list_host_keys.return_value = _mock_host_keys()

        rotate(
            function_app="func-test",
            resource_group="rg-test",
            key_vault="kv-test",
            dry_run=True,
            credential=_mock_credential(),
            subscription_id=SUB_ID,
        )

        mock_web.web_apps.create_or_update_host_secret.assert_not_called()
        mock_secret_cls.return_value.set_secret.assert_not_called()


class TestKeyStored:
    """After rotation, the new key must be saved in Key Vault."""

    @patch("scripts.rotate_function_key.SecretClient")
    @patch("scripts.rotate_function_key.WebSiteManagementClient")
    def test_new_key_stored_in_vault(self, mock_web_cls, mock_secret_cls):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        new_key_name = f"power-automate-{today}"

        mock_web = mock_web_cls.return_value
        mock_web.web_apps.list_host_keys.side_effect = [
            _mock_host_keys({}),
            _mock_host_keys({new_key_name: "generated-secret-value"}),
        ]

        mock_secret = mock_secret_cls.return_value

        rotate(
            function_app="func-test",
            resource_group="rg-test",
            key_vault="kv-test",
            dry_run=False,
            credential=_mock_credential(),
            subscription_id=SUB_ID,
        )

        mock_web.web_apps.create_or_update_host_secret.assert_called_once()
        mock_secret.set_secret.assert_called_once_with(
            "function-app-key",
            "generated-secret-value",
            content_type="Function App host key for Power Automate",
        )


class TestKeyNaming:
    """Generated key names must follow the power-automate-YYYY-MM-DD pattern."""

    @patch("scripts.rotate_function_key.SecretClient")
    @patch("scripts.rotate_function_key.WebSiteManagementClient")
    def test_key_name_includes_date(self, mock_web_cls, mock_secret_cls):
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        expected_name = f"power-automate-{today}"

        mock_web = mock_web_cls.return_value
        mock_web.web_apps.list_host_keys.side_effect = [
            _mock_host_keys({}),
            _mock_host_keys({expected_name: "val"}),
        ]

        rotate(
            function_app="func-test",
            resource_group="rg-test",
            key_vault="kv-test",
            dry_run=False,
            credential=_mock_credential(),
            subscription_id=SUB_ID,
        )

        call_args = mock_web.web_apps.create_or_update_host_secret.call_args
        actual_key_name = call_args[0][3]  # positional: rg, app, slot, key_name
        assert re.match(r"^power-automate-\d{4}-\d{2}-\d{2}$", actual_key_name)
        assert actual_key_name == expected_name


class TestErrorHandling:
    """Graceful errors when the Function App is not found."""

    @patch("scripts.rotate_function_key.SecretClient")
    @patch("scripts.rotate_function_key.WebSiteManagementClient")
    def test_missing_function_app_error(self, mock_web_cls, mock_secret_cls):
        mock_web = mock_web_cls.return_value
        mock_web.web_apps.list_host_keys.side_effect = Exception(
            "ResourceNotFound: func-missing not found"
        )

        with pytest.raises(SystemExit) as exc_info:
            rotate(
                function_app="func-missing",
                resource_group="rg-test",
                key_vault="kv-test",
                dry_run=False,
                credential=_mock_credential(),
                subscription_id=SUB_ID,
            )

        assert exc_info.value.code == 1
