"""Tests for the HTTP handler."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "functions"))

from shared.models import FieldConfig, FormConfig  # noqa: E402
from process_response.handler import handle_form_response  # noqa: E402


def _make_request(body: dict | None = None, *, raw: bytes | None = None) -> MagicMock:
    """Create a mock ``HttpRequest`` with the given JSON body."""
    req = MagicMock()
    if raw is not None:
        req.get_json.side_effect = ValueError("bad json")
    elif body is not None:
        req.get_json.return_value = body
    else:
        req.get_json.side_effect = ValueError("no body")
    return req


_VALID_PAYLOAD = {
    "form_id": "patient-satisfaction-001",
    "response_id": "resp-1",
    "submitted_at": "2024-01-15T10:30:00Z",
    "respondent_email": "user@example.com",
    "answers": [
        {"question_id": "q1", "question": "Patient Name", "answer": "John Doe"},
        {"question_id": "q4", "question": "Satisfaction Rating", "answer": "5"},
    ],
}

_SAMPLE_CONFIG = FormConfig(
    form_id="patient-satisfaction-001",
    form_name="Patient Satisfaction Survey",
    target_table="patient_satisfaction",
    fields=[
        FieldConfig(
            question_id="q1",
            field_name="patient_name",
            contains_phi=True,
            deid_method="redact",
        ),
        FieldConfig(
            question_id="q4",
            field_name="satisfaction_rating",
            contains_phi=False,
        ),
    ],
)


class TestHandleFormResponse:
    """Tests for handle_form_response()."""

    def test_invalid_json(self) -> None:
        resp = handle_form_response(_make_request(raw=b"not json"))
        assert resp.status_code == 400
        body = json.loads(resp.get_body())
        assert body["status"] == "error"

    def test_missing_form_id(self) -> None:
        payload = {
            "response_id": "r1",
            "submitted_at": "2024-01-15T10:30:00Z",
            "respondent_email": "a@b.com",
            "answers": [{"question_id": "q1", "question": "Q", "answer": "A"}],
        }
        resp = handle_form_response(_make_request(payload))
        assert resp.status_code == 400

    @patch("process_response.handler.get_form_config", return_value=None)
    def test_unknown_form(self, _mock_cfg: MagicMock) -> None:
        payload = {**_VALID_PAYLOAD, "form_id": "unknown-form"}
        resp = handle_form_response(_make_request(payload))
        assert resp.status_code == 404
        body = json.loads(resp.get_body())
        assert "unknown-form" in body["message"].lower() or "Unknown" in body["message"]

    def test_empty_answers(self) -> None:
        payload = {**_VALID_PAYLOAD, "answers": []}
        resp = handle_form_response(_make_request(payload))
        assert resp.status_code == 400
        body = json.loads(resp.get_body())
        assert "empty" in body["message"].lower()

    @patch("process_response.handler.write_to_lakehouse", return_value="mock/path.parquet")
    @patch("process_response.handler.get_form_config", return_value=_SAMPLE_CONFIG)
    def test_valid_payload_success(
        self, _mock_cfg: MagicMock, _mock_write: MagicMock
    ) -> None:
        resp = handle_form_response(_make_request(_VALID_PAYLOAD))
        assert resp.status_code == 200
        body = json.loads(resp.get_body())
        assert body["status"] == "success"
        assert body["response_id"] == "resp-1"

    @patch(
        "process_response.handler.write_to_lakehouse",
        side_effect=RuntimeError("connection failed"),
    )
    @patch("process_response.handler.get_form_config", return_value=_SAMPLE_CONFIG)
    def test_onelake_failure_returns_502(
        self, _mock_cfg: MagicMock, _mock_write: MagicMock
    ) -> None:
        resp = handle_form_response(_make_request(_VALID_PAYLOAD))
        assert resp.status_code == 502
