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
) -> dict:
    """Return a complete Power Automate / Logic Apps workflow definition dict."""
    return {
        "$schema": "https://schema.management.azure.com/providers/Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#",
        "contentVersion": "1.0.0.0",
        "parameters": {
            "$connections": {
                "defaultValue": {},
                "type": "Object",
            },
        },
        "triggers": {
            "When_a_new_response_is_submitted": {
                "type": "OpenApiConnectionTrigger",
                "inputs": {
                    "host": {
                        "connection": {
                            "name": "@parameters('$connections')['microsoftforms']['connectionId']",
                        },
                        "api": {
                            "id": "/providers/Microsoft.PowerApps/apis/shared_microsoftforms",
                        },
                    },
                    "method": "get",
                    "path": "/trigger/api/forms/@{encodeURIComponent('" + form_config.form_id + "')}/response",
                },
                "splitOn": "@triggerBody()",
                "recurrence": {
                    "frequency": "Minute",
                    "interval": 1,
                },
                "metadata": {
                    "form_id": form_config.form_id,
                    "form_name": form_config.form_name,
                },
            },
        },
        "actions": {
            "Get_response_details": {
                "type": "OpenApiConnection",
                "runAfter": {},
                "inputs": {
                    "host": {
                        "connection": {
                            "name": "@parameters('$connections')['microsoftforms']['connectionId']",
                        },
                        "api": {
                            "id": "/providers/Microsoft.PowerApps/apis/shared_microsoftforms",
                        },
                    },
                    "method": "get",
                    "path": "/api/forms/@{encodeURIComponent('"
                    + form_config.form_id
                    + "')}/responses/@{encodeURIComponent(triggerBody()?['resourceData']?['responseId'])}",
                },
            },
            "Get_secret": {
                "type": "OpenApiConnection",
                "runAfter": {
                    "Get_response_details": ["Succeeded"],
                },
                "inputs": {
                    "host": {
                        "connection": {
                            "name": "@parameters('$connections')['keyvault']['connectionId']",
                        },
                        "api": {
                            "id": "/providers/Microsoft.PowerApps/apis/shared_keyvault",
                        },
                    },
                    "method": "get",
                    "path": f"/secrets/@{{encodeURIComponent('function-app-key')}}/value",
                },
            },
            "HTTP_POST_to_Azure_Function": {
                "type": "Http",
                "runAfter": {
                    "Get_secret": ["Succeeded"],
                },
                "inputs": {
                    "method": "POST",
                    "uri": f"{function_app_url.rstrip('/')}/api/process-response",
                    "headers": {
                        "Content-Type": "application/json",
                        "x-functions-key": "@body('Get_secret')?['value']",
                    },
                    "body": {
                        "form_id": form_config.form_id,
                        "response_id": "@{triggerBody()?['resourceData']?['responseId']}",
                        "submitted_at": "@{utcNow()}",
                        "respondent_email": "@{body('Get_response_details')?['responder']}",
                        "answers": "@{body('Get_response_details')?['responses']}",
                    },
                },
            },
            "Check_HTTP_status": {
                "type": "If",
                "runAfter": {
                    "HTTP_POST_to_Azure_Function": ["Succeeded", "Failed"],
                },
                "expression": {
                    "not": {
                        "equals": [
                            "@outputs('HTTP_POST_to_Azure_Function')['statusCode']",
                            200,
                        ],
                    },
                },
                "actions": {
                    "Send_error_notification": {
                        "type": "OpenApiConnection",
                        "runAfter": {},
                        "inputs": {
                            "host": {
                                "connection": {
                                    "name": "@parameters('$connections')['office365']['connectionId']",
                                },
                                "api": {
                                    "id": "/providers/Microsoft.PowerApps/apis/shared_office365",
                                },
                            },
                            "method": "post",
                            "path": "/v2/Mail",
                            "body": {
                                "To": "admin@contoso.com",
                                "Subject": f"Forms-to-Fabric Pipeline Error — {form_config.form_name}",
                                "Body": (
                                    "<p><strong>Pipeline Error</strong></p>"
                                    f"<p>Form: {form_config.form_name} ({form_config.form_id})</p>"
                                    "<p>Response ID: @{triggerBody()?['resourceData']?['responseId']}</p>"
                                    "<p>HTTP Status: @{outputs('HTTP_POST_to_Azure_Function')['statusCode']}</p>"
                                    "<p>Details:</p><pre>@{body('HTTP_POST_to_Azure_Function')}</pre>"
                                ),
                                "Importance": "High",
                            },
                        },
                    },
                },
                "else": {
                    "actions": {},
                },
            },
        },
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
            json.dumps({"status": "error", "message": "Missing required query parameter: form_id"}),
            status_code=400,
            mimetype="application/json",
        )

    function_app_url = req.params.get(
        "function_app_url",
        os.environ.get("FUNCTION_APP_URL", "https://<your-function-app>.azurewebsites.net"),
    )
    key_vault_name = req.params.get(
        "key_vault_name",
        os.environ.get("KEY_VAULT_NAME", "<your-key-vault>"),
    )

    try:
        definition = generate_flow_definition(form_id, function_app_url, key_vault_name)
    except KeyError:
        return func.HttpResponse(
            json.dumps({"status": "error", "message": f"Form '{form_id}' not found in registry"}),
            status_code=404,
            mimetype="application/json",
        )

    return func.HttpResponse(
        json.dumps(definition, indent=2),
        status_code=200,
        mimetype="application/json",
    )
