"""Tests for the registration flow builder module."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "functions"))

from shared.registration_flow_builder import (
    build_registration_flow_create_body,
    build_registration_flow_definition,
)

_REG_FORM_ID = "v4j5cvGGr0GRqy1_TEST"
_FUNC_URL = "https://func-forms-dev-abc.azurewebsites.net"
_FUNC_KEY = "test-key-1234"
_ENV_ID = "Default-00000000-0000-0000-0000-000000000000"
_ALERT_EMAIL = "admin@contoso.com"


class TestBuildRegistrationFlowDefinition:
    """Unit tests for the registration flow workflow definition."""

    def _build(self) -> dict:
        return build_registration_flow_definition(
            registration_form_id=_REG_FORM_ID,
            function_app_url=_FUNC_URL,
            function_app_key=_FUNC_KEY,
            flow_environment_id=_ENV_ID,
            alert_email=_ALERT_EMAIL,
        )

    def test_schema_present(self) -> None:
        defn = self._build()
        assert "$schema" in defn
        assert "workflowdefinition" in defn["$schema"]

    def test_trigger_uses_registration_form(self) -> None:
        defn = self._build()
        trigger = defn["triggers"]["When_a_new_response_is_submitted"]
        assert trigger["inputs"]["parameters"]["form_id"] == _REG_FORM_ID
        assert trigger["type"] == "OpenApiConnectionWebhook"

    def test_get_response_details_action(self) -> None:
        defn = self._build()
        action = defn["actions"]["Get_response_details"]
        assert action["inputs"]["parameters"]["form_id"] == _REG_FORM_ID
        assert action["inputs"]["host"]["operationId"] == "GetFormResponseById"

    def test_register_form_http_action(self) -> None:
        defn = self._build()
        action = defn["actions"]["RegisterForm"]
        assert action["type"] == "Http"
        assert action["inputs"]["method"] == "POST"
        assert "/api/register-form" in action["inputs"]["uri"]
        assert action["inputs"]["headers"]["x-functions-key"] == _FUNC_KEY

    def test_register_form_url_no_trailing_slash(self) -> None:
        defn = build_registration_flow_definition(
            registration_form_id=_REG_FORM_ID,
            function_app_url=_FUNC_URL + "/",
            function_app_key=_FUNC_KEY,
            flow_environment_id=_ENV_ID,
            alert_email=_ALERT_EMAIL,
        )
        uri = defn["actions"]["RegisterForm"]["inputs"]["uri"]
        assert "//" not in uri.replace("https://", "")

    def test_condition_check_action(self) -> None:
        defn = self._build()
        condition = defn["actions"]["Check_registration_success"]
        assert condition["type"] == "If"
        assert "actions" in condition  # success branch
        assert "else" in condition  # failure branch

    def test_success_branch_creates_flow(self) -> None:
        defn = self._build()
        success = defn["actions"]["Check_registration_success"]["actions"]
        action = success["Create_per_form_flow"]
        assert action["type"] == "OpenApiConnection"
        assert "shared_webcontents" in action["inputs"]["host"]["apiId"]
        assert _ENV_ID in action["inputs"]["parameters"]["url"]

    def test_failure_branch_sends_email(self) -> None:
        defn = self._build()
        failure = defn["actions"]["Check_registration_success"]["else"]["actions"]
        action = failure["Send_error_notification"]
        assert action["type"] == "OpenApiConnection"
        assert action["inputs"]["parameters"]["emailMessage/To"] == _ALERT_EMAIL
        assert "shared_office365" in action["inputs"]["host"]["apiId"]

    def test_condition_runs_after_register(self) -> None:
        defn = self._build()
        run_after = defn["actions"]["Check_registration_success"]["runAfter"]
        assert "RegisterForm" in run_after
        assert "Succeeded" in run_after["RegisterForm"]
        assert "Failed" in run_after["RegisterForm"]


class TestBuildRegistrationFlowCreateBody:
    """Unit tests for the full Flow API create body."""

    def _build(self) -> dict:
        return build_registration_flow_create_body(
            registration_form_id=_REG_FORM_ID,
            function_app_url=_FUNC_URL,
            function_app_key=_FUNC_KEY,
            flow_environment_id=_ENV_ID,
            alert_email=_ALERT_EMAIL,
        )

    def test_has_properties_wrapper(self) -> None:
        body = self._build()
        assert "properties" in body
        assert "displayName" in body["properties"]
        assert "definition" in body["properties"]

    def test_display_name(self) -> None:
        body = self._build()
        assert body["properties"]["displayName"] == "Forms to Fabric: Register New Form"

    def test_state_is_started(self) -> None:
        body = self._build()
        assert body["properties"]["state"] == "Started"

    def test_connection_references_present(self) -> None:
        body = self._build()
        refs = body["properties"]["connectionReferences"]
        assert "shared_microsoftforms" in refs
        assert "shared_office365" in refs
        assert "shared_webcontents" in refs

    def test_custom_connection_names(self) -> None:
        body = build_registration_flow_create_body(
            registration_form_id=_REG_FORM_ID,
            function_app_url=_FUNC_URL,
            function_app_key=_FUNC_KEY,
            flow_environment_id=_ENV_ID,
            alert_email=_ALERT_EMAIL,
            forms_connection_name="my_forms",
            outlook_connection_name="my_outlook",
            webcontents_connection_name="my_entra_http",
        )
        refs = body["properties"]["connectionReferences"]
        assert refs["shared_microsoftforms"]["connectionName"] == "my_forms"
        assert refs["shared_office365"]["connectionName"] == "my_outlook"
        assert refs["shared_webcontents"]["connectionName"] == "my_entra_http"

    def test_definition_embeds_form_id(self) -> None:
        body = self._build()
        defn = body["properties"]["definition"]
        trigger = defn["triggers"]["When_a_new_response_is_submitted"]
        assert trigger["inputs"]["parameters"]["form_id"] == _REG_FORM_ID
