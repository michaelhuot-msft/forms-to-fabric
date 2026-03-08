"""Tests for the GET /api/openapi endpoint."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "functions"))

from openapi_spec.handler import build_openapi_spec, handle_openapi_spec  # noqa: E402

# ---------------------------------------------------------------------------
# build_openapi_spec() unit tests
# ---------------------------------------------------------------------------


class TestBuildOpenApiSpec:
    """Validate the structure of the generated OpenAPI 3.0.3 document."""

    def test_openapi_version(self) -> None:
        spec = build_openapi_spec()
        assert spec["openapi"] == "3.0.3"

    def test_info_block(self) -> None:
        spec = build_openapi_spec()
        info = spec["info"]
        assert info["title"] == "Forms to Fabric API"
        assert "version" in info
        assert "description" in info

    def test_servers_block(self) -> None:
        spec = build_openapi_spec()
        servers = spec["servers"]
        assert isinstance(servers, list)
        assert len(servers) >= 1
        server_url: str = servers[0]["url"]
        assert server_url.endswith(".azurewebsites.net/api")

    def test_global_security_uses_function_key(self) -> None:
        spec = build_openapi_spec()
        security = spec["security"]
        assert any("FunctionKey" in entry for entry in security)

    def test_security_schemes_defined(self) -> None:
        spec = build_openapi_spec()
        schemes = spec["components"]["securitySchemes"]
        assert "FunctionKey" in schemes
        assert schemes["FunctionKey"]["type"] == "apiKey"
        assert schemes["FunctionKey"]["in"] == "header"
        assert schemes["FunctionKey"]["name"] == "x-functions-key"

    def test_function_key_query_scheme_defined(self) -> None:
        spec = build_openapi_spec()
        schemes = spec["components"]["securitySchemes"]
        assert "FunctionKeyQuery" in schemes
        assert schemes["FunctionKeyQuery"]["in"] == "query"
        assert schemes["FunctionKeyQuery"]["name"] == "code"

    # -- Schema components --

    def test_answer_schema(self) -> None:
        spec = build_openapi_spec()
        answer = spec["components"]["schemas"]["Answer"]
        assert answer["type"] == "object"
        assert set(answer["required"]) == {"question_id", "question", "answer"}
        for field in ("question_id", "question", "answer"):
            assert field in answer["properties"]

    def test_form_response_schema(self) -> None:
        spec = build_openapi_spec()
        schema = spec["components"]["schemas"]["FormResponse"]
        assert schema["type"] == "object"
        assert "form_id" in schema["required"]
        props = schema["properties"]
        assert "form_id" in props
        assert "answers" in props
        assert props["answers"]["items"]["$ref"] == "#/components/schemas/Answer"
        assert "raw_response" in props

    def test_processing_result_schema(self) -> None:
        spec = build_openapi_spec()
        schema = spec["components"]["schemas"]["ProcessingResult"]
        assert schema["type"] == "object"
        props = schema["properties"]
        for field in (
            "status",
            "response_id",
            "form_id",
            "raw_path",
            "curated_path",
            "message",
        ):
            assert field in props
        assert props["status"]["enum"] == ["success", "error"]

    def test_register_form_request_schema(self) -> None:
        spec = build_openapi_spec()
        schema = spec["components"]["schemas"]["RegisterFormRequest"]
        assert schema["type"] == "object"
        required = schema["required"]
        assert "form_url" in required
        assert "has_phi" in required

    def test_activate_form_request_schema(self) -> None:
        spec = build_openapi_spec()
        schema = spec["components"]["schemas"]["ActivateFormRequest"]
        assert "form_id" in schema["required"]

    def test_error_response_schema(self) -> None:
        spec = build_openapi_spec()
        schema = spec["components"]["schemas"]["ErrorResponse"]
        assert "error" in schema["properties"]

    # -- Paths --

    def test_all_four_http_endpoints_present(self) -> None:
        spec = build_openapi_spec()
        paths = spec["paths"]
        assert "/process-response" in paths
        assert "/register-form" in paths
        assert "/activate-form" in paths
        assert "/generate-flow" in paths

    def test_process_response_is_post(self) -> None:
        spec = build_openapi_spec()
        assert "post" in spec["paths"]["/process-response"]

    def test_register_form_is_post(self) -> None:
        spec = build_openapi_spec()
        assert "post" in spec["paths"]["/register-form"]

    def test_activate_form_is_post(self) -> None:
        spec = build_openapi_spec()
        assert "post" in spec["paths"]["/activate-form"]

    def test_generate_flow_is_get(self) -> None:
        spec = build_openapi_spec()
        assert "get" in spec["paths"]["/generate-flow"]

    def test_process_response_request_body_refs_form_response(self) -> None:
        spec = build_openapi_spec()
        op = spec["paths"]["/process-response"]["post"]
        schema_ref = op["requestBody"]["content"]["application/json"]["schema"]
        assert schema_ref["$ref"] == "#/components/schemas/FormResponse"

    def test_process_response_has_expected_status_codes(self) -> None:
        spec = build_openapi_spec()
        responses = spec["paths"]["/process-response"]["post"]["responses"]
        for code in ("200", "400", "403", "404", "502", "503"):
            assert code in responses, f"Missing status code {code} in /process-response"

    def test_activate_form_has_404(self) -> None:
        spec = build_openapi_spec()
        responses = spec["paths"]["/activate-form"]["post"]["responses"]
        assert "404" in responses

    def test_generate_flow_has_required_form_id_parameter(self) -> None:
        spec = build_openapi_spec()
        params = spec["paths"]["/generate-flow"]["get"]["parameters"]
        form_id_param = next((p for p in params if p["name"] == "form_id"), None)
        assert form_id_param is not None
        assert form_id_param["required"] is True
        assert form_id_param["in"] == "query"

    def test_generate_flow_optional_params(self) -> None:
        spec = build_openapi_spec()
        params = spec["paths"]["/generate-flow"]["get"]["parameters"]
        param_names = {p["name"] for p in params}
        assert "function_app_url" in param_names
        assert "key_vault_name" in param_names

    def test_register_form_response_uses_oneOf(self) -> None:
        spec = build_openapi_spec()
        ok_response = spec["paths"]["/register-form"]["post"]["responses"]["200"]
        schema = ok_response["content"]["application/json"]["schema"]
        assert "oneOf" in schema

    def test_operation_ids_are_unique(self) -> None:
        spec = build_openapi_spec()
        operation_ids = []
        for path_item in spec["paths"].values():
            for method_obj in path_item.values():
                if "operationId" in method_obj:
                    operation_ids.append(method_obj["operationId"])
        assert len(operation_ids) == len(set(operation_ids)), (
            "Duplicate operationIds found"
        )

    def test_tags_assigned_to_all_operations(self) -> None:
        spec = build_openapi_spec()
        for path, path_item in spec["paths"].items():
            for method, op in path_item.items():
                assert "tags" in op, f"Missing tags on {method.upper()} {path}"
                assert len(op["tags"]) >= 1

    def test_spec_is_json_serializable(self) -> None:
        spec = build_openapi_spec()
        serialised = json.dumps(spec)
        assert len(serialised) > 0
        roundtripped = json.loads(serialised)
        assert roundtripped["openapi"] == "3.0.3"


# ---------------------------------------------------------------------------
# handle_openapi_spec() HTTP handler tests
# ---------------------------------------------------------------------------


class TestHandleOpenApiSpec:
    """Integration tests for the HTTP handler."""

    def _make_request(self) -> MagicMock:
        req = MagicMock()
        req.params = {}
        return req

    def test_returns_200(self) -> None:
        resp = handle_openapi_spec(self._make_request())
        assert resp.status_code == 200

    def test_content_type_is_json(self) -> None:
        resp = handle_openapi_spec(self._make_request())
        assert "application/json" in resp.mimetype

    def test_body_is_valid_json(self) -> None:
        resp = handle_openapi_spec(self._make_request())
        body = json.loads(resp.get_body())
        assert isinstance(body, dict)

    def test_body_contains_openapi_key(self) -> None:
        resp = handle_openapi_spec(self._make_request())
        body = json.loads(resp.get_body())
        assert body["openapi"].startswith("3.")

    def test_cors_header_present(self) -> None:
        resp = handle_openapi_spec(self._make_request())
        assert resp.headers.get("Access-Control-Allow-Origin") == "*"

    @pytest.mark.parametrize(
        "endpoint",
        ["/process-response", "/register-form", "/activate-form", "/generate-flow"],
    )
    def test_all_endpoints_in_response_body(self, endpoint: str) -> None:
        resp = handle_openapi_spec(self._make_request())
        body = json.loads(resp.get_body())
        assert endpoint in body["paths"], f"{endpoint} missing from spec paths"
