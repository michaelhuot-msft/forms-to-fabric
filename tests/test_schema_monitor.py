"""Tests for the schema monitor that detects form-structure changes."""

from __future__ import annotations

import sys
from pathlib import Path
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# Ensure src/functions is on the import path so `shared.*` resolves.
_functions_dir = str(Path(__file__).resolve().parent.parent / "src" / "functions")
if _functions_dir not in sys.path:
    sys.path.insert(0, _functions_dir)

from shared.graph_client import FormNotFoundError, GraphClient
from shared.models import FieldConfig, FormConfig, SchemaChange, SchemaChangeReport
from monitor_schema.handler import _compare_schema, check_all_forms, send_alert


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_form_config(
    form_id: str = "test-form",
    form_name: str = "Test Form",
    fields: list[dict] | None = None,
) -> FormConfig:
    """Build a minimal FormConfig for testing."""
    if fields is None:
        fields = [
            {"question_id": "q1", "field_name": "Name"},
            {"question_id": "q2", "field_name": "Age"},
        ]
    return FormConfig(
        form_id=form_id,
        form_name=form_name,
        target_table="test_table",
        fields=[FieldConfig(**f) for f in fields],
    )


def _make_live_questions(items: list[tuple[str, str]]) -> list[dict[str, str]]:
    """Build a list of live question dicts from (id, title) tuples."""
    return [{"id": qid, "title": title, "type": "text"} for qid, title in items]


# ---------------------------------------------------------------------------
# _compare_schema unit tests
# ---------------------------------------------------------------------------

class TestCompareSchema:
    """Direct unit tests for the comparison logic."""

    def test_no_changes(self) -> None:
        """No changes when live questions match registry exactly."""
        config = _make_form_config()
        live = _make_live_questions([("q1", "Name"), ("q2", "Age")])

        changes = _compare_schema(config, live)

        assert changes == []

    def test_added_question(self) -> None:
        """A question present in live but absent from registry is 'added'."""
        config = _make_form_config()
        live = _make_live_questions([
            ("q1", "Name"),
            ("q2", "Age"),
            ("q3", "Email"),
        ])

        changes = _compare_schema(config, live)

        assert len(changes) == 1
        assert changes[0].change_type == "added"
        assert changes[0].question_id == "q3"
        assert changes[0].new_value == "Email"

    def test_removed_question(self) -> None:
        """A question in registry but missing from live is 'removed'."""
        config = _make_form_config()
        live = _make_live_questions([("q1", "Name")])

        changes = _compare_schema(config, live)

        assert len(changes) == 1
        assert changes[0].change_type == "removed"
        assert changes[0].question_id == "q2"
        assert changes[0].field_name == "Age"

    def test_renamed_question(self) -> None:
        """A question with the same ID but different title is 'renamed'."""
        config = _make_form_config()
        live = _make_live_questions([("q1", "Full Name"), ("q2", "Age")])

        changes = _compare_schema(config, live)

        assert len(changes) == 1
        assert changes[0].change_type == "renamed"
        assert changes[0].question_id == "q1"
        assert changes[0].old_value == "Name"
        assert changes[0].new_value == "Full Name"

    def test_multiple_changes(self) -> None:
        """Multiple change types can appear in a single comparison."""
        config = _make_form_config()
        live = _make_live_questions([
            ("q1", "Full Name"),   # renamed
            ("q3", "Department"),  # added  (q2 is missing → removed)
        ])

        changes = _compare_schema(config, live)

        types = {c.change_type for c in changes}
        assert types == {"added", "removed", "renamed"}
        assert len(changes) == 3


# ---------------------------------------------------------------------------
# check_all_forms integration tests (mocked Graph client + config)
# ---------------------------------------------------------------------------

class TestCheckAllForms:
    """Integration tests for check_all_forms with a mocked Graph client."""

    @patch("monitor_schema.handler.get_all_form_configs")
    def test_detects_added_question(self, mock_configs: MagicMock) -> None:
        config = _make_form_config()
        mock_configs.return_value = {config.form_id: config}

        mock_client = MagicMock(spec=GraphClient)
        mock_client.get_form_questions.return_value = _make_live_questions([
            ("q1", "Name"),
            ("q2", "Age"),
            ("q3", "New Question"),
        ])

        reports = check_all_forms(client=mock_client)

        assert len(reports) == 1
        assert reports[0].has_changes is True
        added = [c for c in reports[0].changes if c.change_type == "added"]
        assert len(added) == 1
        assert added[0].question_id == "q3"

    @patch("monitor_schema.handler.get_all_form_configs")
    def test_detects_removed_question(self, mock_configs: MagicMock) -> None:
        config = _make_form_config()
        mock_configs.return_value = {config.form_id: config}

        mock_client = MagicMock(spec=GraphClient)
        mock_client.get_form_questions.return_value = _make_live_questions([
            ("q1", "Name"),
        ])

        reports = check_all_forms(client=mock_client)

        assert len(reports) == 1
        assert reports[0].has_changes is True
        removed = [c for c in reports[0].changes if c.change_type == "removed"]
        assert len(removed) == 1
        assert removed[0].question_id == "q2"

    @patch("monitor_schema.handler.get_all_form_configs")
    def test_detects_renamed_question(self, mock_configs: MagicMock) -> None:
        config = _make_form_config()
        mock_configs.return_value = {config.form_id: config}

        mock_client = MagicMock(spec=GraphClient)
        mock_client.get_form_questions.return_value = _make_live_questions([
            ("q1", "Patient Full Name"),
            ("q2", "Age"),
        ])

        reports = check_all_forms(client=mock_client)

        assert len(reports) == 1
        assert reports[0].has_changes is True
        renamed = [c for c in reports[0].changes if c.change_type == "renamed"]
        assert len(renamed) == 1
        assert renamed[0].old_value == "Name"
        assert renamed[0].new_value == "Patient Full Name"

    @patch("monitor_schema.handler.get_all_form_configs")
    def test_no_changes_detected(self, mock_configs: MagicMock) -> None:
        config = _make_form_config()
        mock_configs.return_value = {config.form_id: config}

        mock_client = MagicMock(spec=GraphClient)
        mock_client.get_form_questions.return_value = _make_live_questions([
            ("q1", "Name"),
            ("q2", "Age"),
        ])

        reports = check_all_forms(client=mock_client)

        assert len(reports) == 1
        assert reports[0].has_changes is False
        assert reports[0].changes == []

    @patch("monitor_schema.handler.get_all_form_configs")
    def test_form_not_found_404(self, mock_configs: MagicMock) -> None:
        config = _make_form_config()
        mock_configs.return_value = {config.form_id: config}

        mock_client = MagicMock(spec=GraphClient)
        mock_client.get_form_questions.side_effect = FormNotFoundError(config.form_id)

        reports = check_all_forms(client=mock_client)

        assert len(reports) == 1
        assert reports[0].has_changes is True
        assert reports[0].changes[0].change_type == "removed"
        assert reports[0].changes[0].question_id == "*"


# ---------------------------------------------------------------------------
# send_alert tests
# ---------------------------------------------------------------------------

class TestSendAlert:
    """Tests for the send_alert logging/notification path."""

    def test_logs_changes(self, caplog: pytest.LogCaptureFixture) -> None:
        report = SchemaChangeReport(
            form_id="f1",
            form_name="Test",
            checked_at=datetime.now(timezone.utc),
            changes=[
                SchemaChange(change_type="added", question_id="q9", new_value="New Q"),
            ],
            has_changes=True,
        )

        with caplog.at_level("WARNING"):
            send_alert([report])

        assert "ADDED" in caplog.text
        assert "q9" in caplog.text

    @patch.dict("os.environ", {"ADMIN_ALERT_EMAIL": "admin@example.com"})
    def test_email_logged_when_env_set(self, caplog: pytest.LogCaptureFixture) -> None:
        report = SchemaChangeReport(
            form_id="f1",
            form_name="Test",
            checked_at=datetime.now(timezone.utc),
            changes=[
                SchemaChange(change_type="removed", question_id="q1", old_value="X"),
            ],
            has_changes=True,
        )

        with caplog.at_level("INFO"):
            send_alert([report])

        assert "admin@example.com" in caplog.text
