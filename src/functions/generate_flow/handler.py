"""Generate an importable Power Automate flow definition for a registered form."""

from __future__ import annotations

import json
import logging
import os

import azure.functions as func

from shared.config import get_form_config
from shared.models import FormConfig

logger = logging.getLogger(__name__)


def _build_flow_definition(
    form_config: FormConfig,
    function_app_url: str,
    key_vault_name: str,
    admin_email: str = "",
) -> dict:
    """Return a Power Automate flow definition in the correct PA REST API format."""
    if not admin_email:
        admin_email = os.environ.get("ADMIN_EMAIL", "admin@contoso.com")

    func_url = f"{function_app_url.rstrip('/')}/api/process-response"
    func_key = os.environ.get("FUNCTION_APP_KEY", "")

    return {
        "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {
            "$authentication": {"defaultValue": {}, "type": "SecureObject"},
            "$connections": {"defaultValue": {}, "type": "Object"},
        },
        "triggers": {
            "When_a_new_response_is_submitted": {
                "splitOn": "@triggerOutputs()?['body/value']",
                "type": "OpenApiConnectionWebhook",
                "inputs": {
                    "parameters": {"form_id": form_config.form_id},
                    "host": {
                        "apiId": "/providers/Microsoft.PowerApps/apis/shared_microsoftforms",
                        "operationId": "CreateFormWebhook",
                        "connectionName": "shared_microsoftforms",
                    },
                },
            },
        },
        "actions": {
            "Get_response_details": {
                "runAfter": {},
                "type": "OpenApiConnection",
                "inputs": {
                    "parameters": {
                        "form_id": form_config.form_id,
                        "response_id": "@triggerOutputs()?['body/resourceData/responseId']",
                    },
                    "host": {
                        "apiId": "/providers/Microsoft.PowerApps/apis/shared_microsoftforms",
                        "operationId": "GetFormResponseById",
                        "connectionName": "shared_microsoftforms",
                    },
                },
            },
            "HTTP_POST_to_Azure_Function": {
                "runAfter": {"Get_response_details": ["Succeeded"]},
                "type": "Http",
                "inputs": {
                    "method": "POST",
                    "uri": func_url,
                    "headers": {
                        "Content-Type": "application/json",
                        "x-functions-key": func_key,
                    },
                    "body": {
                        "form_id": form_config.form_id,
                        "raw_response": "@body('Get_response_details')",
                    },
                },
            },
        },
        "outputs": {},
    }


def generate_flow_definition(
    form_id: str,
    function_app_url: str,
    key_vault_name: str,
) -> dict:
    """Build a Power Automate flow definition for *form_id*.

    Raises ``KeyError`` if the form is not found in the registry.
    """
    form_config = get_form_config(form_id)
    if form_config is None:
        raise KeyError(f"Form '{form_id}' not found in registry")

    return _build_flow_definition(form_config, function_app_url, key_vault_name)


def handle_generate_flow(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP handler: return a Power Automate flow definition JSON."""
    form_id = req.params.get("form_id")
    if not form_id:
        return func.HttpResponse(
            json.dumps(
                {
                    "status": "error",
                    "message": "Missing required query parameter: form_id",
                }
            ),
            status_code=400,
            mimetype="application/json",
        )

    function_app_url = req.params.get(
        "function_app_url",
        os.environ.get(
            "FUNCTION_APP_URL", "https://<your-function-app>.azurewebsites.net"
        ),
    )
    key_vault_name = req.params.get(
        "key_vault_name",
        os.environ.get("KEY_VAULT_NAME", "<your-key-vault>"),
    )

    try:
        definition = generate_flow_definition(form_id, function_app_url, key_vault_name)
    except KeyError:
        return func.HttpResponse(
            json.dumps(
                {
                    "status": "error",
                    "message": f"Form '{form_id}' not found in registry",
                }
            ),
            status_code=404,
            mimetype="application/json",
        )

    return func.HttpResponse(
        json.dumps(definition, indent=2),
        status_code=200,
        mimetype="application/json",
    )
