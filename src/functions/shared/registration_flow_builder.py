"""Build a Power Automate registration flow definition.

Generates the Logic App workflow definition for the self-service form
registration flow.  This flow:

1. Triggers when a clinician submits the "Register Your Form" Microsoft Form.
2. Retrieves the full response details.
3. POSTs the raw response to ``/api/register-form`` on the Azure Function App.
4. On success, POSTs the returned ``flow_create_body`` to the Flow Management
   API via the HTTP with Microsoft Entra ID connector to create the per-form
   data pipeline flow.
5. On failure, sends an admin notification email.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


def build_registration_flow_definition(
    *,
    registration_form_id: str,
    function_app_url: str,
    function_app_key: str,
    flow_environment_id: str,
    alert_email: str,
) -> dict:
    """Return the Logic App workflow definition for the registration flow.

    Parameters
    ----------
    registration_form_id:
        The Microsoft Form ID for the "Register Your Form" intake form.
    function_app_url:
        Base URL of the deployed Azure Function App
        (e.g. ``https://func-forms-dev-abc123.azurewebsites.net``).
    function_app_key:
        Function or host key used to authenticate the HTTP POST.
    flow_environment_id:
        Power Platform environment ID (typically ``Default-<tenant-id>``).
    alert_email:
        Email address or distribution list for registration failure alerts.
    """
    register_url = f"{function_app_url.rstrip('/')}/api/register-form"
    flow_api_path = (
        f"/providers/Microsoft.ProcessSimple"
        f"/environments/{flow_environment_id}/flows"
        "?api-version=2016-11-01"
    )

    return {
        "$schema": (
            "https://schema.management.azure.com/providers/"
            "Microsoft.Logic/schemas/2016-06-01/workflowdefinition.json#"
        ),
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
                    "parameters": {"form_id": registration_form_id},
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
                        "form_id": registration_form_id,
                        "response_id": "@triggerOutputs()?['body/resourceData/responseId']",
                    },
                    "host": {
                        "apiId": "/providers/Microsoft.PowerApps/apis/shared_microsoftforms",
                        "operationId": "GetFormResponseById",
                        "connectionName": "shared_microsoftforms",
                    },
                },
            },
            "RegisterForm": {
                "runAfter": {"Get_response_details": ["Succeeded"]},
                "type": "Http",
                "inputs": {
                    "method": "POST",
                    "uri": register_url,
                    "headers": {
                        "Content-Type": "application/json",
                        "x-functions-key": function_app_key,
                    },
                    "body": {
                        "form_id": registration_form_id,
                        "raw_response": "@body('Get_response_details')",
                    },
                },
                "runtimeConfiguration": {
                    "contentTransfer": {"transferMode": "Chunked"},
                },
            },
            "Check_registration_success": {
                "runAfter": {
                    "RegisterForm": ["Succeeded", "Failed", "TimedOut"],
                },
                "type": "If",
                "expression": {
                    "and": [
                        {
                            "equals": [
                                "@outputs('RegisterForm')['statusCode']",
                                200,
                            ]
                        }
                    ]
                },
                "actions": {
                    "Create_per_form_flow": {
                        "runAfter": {},
                        "type": "OpenApiConnection",
                        "inputs": {
                            "parameters": {
                                "request/method": "POST",
                                "request/url": flow_api_path,
                                "request/body": "@body('RegisterForm')?['flow_create_body']",
                                "request/headers": {
                                    "Content-Type": "application/json",
                                },
                            },
                            "host": {
                                "apiId": "/providers/Microsoft.PowerApps/apis/shared_webcontents",
                                "operationId": "InvokeHttp",
                                "connectionName": "shared_webcontents",
                            },
                        },
                    },
                },
                "else": {
                    "actions": {
                        "Send_error_notification": {
                            "runAfter": {},
                            "type": "OpenApiConnection",
                            "inputs": {
                                "parameters": {
                                    "emailMessage/To": alert_email,
                                    "emailMessage/Subject": (
                                        "Forms to Fabric - Registration failure"
                                    ),
                                    "emailMessage/Body": (
                                        "<p><b>A form registration failed.</b></p>"
                                        "<p><b>HTTP Status:</b> "
                                        "@{outputs('RegisterForm')?['statusCode']}</p>"
                                        "<p><b>Error:</b></p>"
                                        "<pre>@{body('RegisterForm')}</pre>"
                                        "<p><b>Submitted response:</b></p>"
                                        "<pre>@{body('Get_response_details')}</pre>"
                                        "<p><b>Time:</b> @{utcNow()}</p>"
                                        "<hr/>"
                                        "<p><i>Review the registration flow run "
                                        "history and register the form manually "
                                        "if needed.</i></p>"
                                    ),
                                    "emailMessage/Importance": "High",
                                },
                                "host": {
                                    "apiId": "/providers/Microsoft.PowerApps/apis/shared_office365",
                                    "operationId": "SendEmailV2",
                                    "connectionName": "shared_office365",
                                },
                            },
                        },
                    },
                },
            },
        },
        "outputs": {},
    }


def build_registration_flow_create_body(
    *,
    registration_form_id: str,
    function_app_url: str,
    function_app_key: str,
    flow_environment_id: str,
    alert_email: str,
    forms_connection_name: str = "shared_microsoftforms",
    outlook_connection_name: str = "shared_office365",
    webcontents_connection_name: str = "shared_webcontents",
) -> dict:
    """Return the full Flow API POST body for creating the registration flow.

    This is the payload sent to
    ``POST /providers/Microsoft.ProcessSimple/environments/{env}/flows``.
    """
    definition = build_registration_flow_definition(
        registration_form_id=registration_form_id,
        function_app_url=function_app_url,
        function_app_key=function_app_key,
        flow_environment_id=flow_environment_id,
        alert_email=alert_email,
    )

    return {
        "properties": {
            "displayName": "Forms to Fabric: Register New Form",
            "definition": definition,
            "state": "Started",
            "connectionReferences": {
                "shared_microsoftforms": {
                    "id": "/providers/Microsoft.PowerApps/apis/shared_microsoftforms",
                    "connectionName": forms_connection_name,
                    "source": "Embedded",
                },
                "shared_office365": {
                    "id": "/providers/Microsoft.PowerApps/apis/shared_office365",
                    "connectionName": outlook_connection_name,
                    "source": "Embedded",
                },
                "shared_webcontents": {
                    "id": "/providers/Microsoft.PowerApps/apis/shared_webcontents",
                    "connectionName": webcontents_connection_name,
                    "source": "Embedded",
                },
            },
        }
    }
