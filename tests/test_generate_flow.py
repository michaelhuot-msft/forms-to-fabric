"""Tests for the generate-flow endpoint."""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "functions"))

from shared.models import FieldConfig, FormConfig  # noqa: E402
from generate_flow.handler import generate_flow_definition, handle_generate_flow  # noqa: E402

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

_FUNC_URL = "https://my-func.azurewebsites.net"
_KV_NAME = "my-keyvault"


def _make_request(params: dict | None = None) -> MagicMock:
    """Create a mock ``HttpRequest`` with query parameters."""
    req = MagicMock()
    req.params = params or {}
    return req


class TestGenerateFlowDefinition:
    """Unit tests for generate_flow_definition()."""

    @patch("generate_flow.handler.get_form_config", return_value=_SAMPLE_CONFIG)
    def test_generates_valid_flow(self, _mock_cfg: MagicMock) -> None:
        result = generate_flow_definition(
            "patient-satisfaction-001", _FUNC_URL, _KV_NAME
        )

        assert "$schema" in result
        assert "contentVersion" in result
        assert "triggers" in result
        assert "actions" in result
        assert "parameters" in result

    @patch("generate_flow.handler.get_form_config", return_value=None)
    def test_form_not_found(self, _mock_cfg: MagicMock) -> None:
        with pytest.raises(KeyError, match="not found"):
            generate_flow_definition("nonexistent-form", _FUNC_URL, _KV_NAME)

    @patch("generate_flow.handler.get_form_config", return_value=_SAMPLE_CONFIG)
    def test_flow_uses_correct_trigger_type(self, _mock_cfg: MagicMock) -> None:
        result = generate_flow_definition(
            "patient-satisfaction-001", _FUNC_URL, _KV_NAME
        )
        trigger = result["triggers"]["When_a_new_response_is_submitted"]
        assert trigger["type"] == "OpenApiConnectionWebhook"
        assert trigger["inputs"]["host"]["operationId"] == "CreateFormWebhook"

    @patch("generate_flow.handler.get_form_config", return_value=_SAMPLE_CONFIG)
    def test_flow_body_has_form_id(self, _mock_cfg: MagicMock) -> None:
        result = generate_flow_definition(
            "patient-satisfaction-001", _FUNC_URL, _KV_NAME
        )
        http_action = result["actions"]["HTTP_POST_to_Azure_Function"]
        body = http_action["inputs"]["body"]

        assert body["form_id"] == "patient-satisfaction-001"


class TestHandleGenerateFlow:
    """Integration tests for the HTTP handler."""

    def test_missing_form_id(self) -> None:
        resp = handle_generate_flow(_make_request({}))
        assert resp.status_code == 400
        body = json.loads(resp.get_body())
        assert "form_id" in body["message"].lower()

    @patch("generate_flow.handler.get_form_config", return_value=None)
    def test_form_not_found_returns_404(self, _mock_cfg: MagicMock) -> None:
        resp = handle_generate_flow(_make_request({"form_id": "unknown"}))
        assert resp.status_code == 404
        body = json.loads(resp.get_body())
        assert "unknown" in body["message"]

    @patch("generate_flow.handler.get_form_config", return_value=_SAMPLE_CONFIG)
    def test_valid_form_returns_200(self, _mock_cfg: MagicMock) -> None:
        resp = handle_generate_flow(
            _make_request({"form_id": "patient-satisfaction-001"})
        )
        assert resp.status_code == 200
        definition = json.loads(resp.get_body())
        assert definition["$schema"].startswith("https://schema.management.azure.com")
        assert "triggers" in definition
        assert "actions" in definition
