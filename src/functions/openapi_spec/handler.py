"""Build and serve the OpenAPI 3.0.3 specification for the Forms to Fabric API."""

from __future__ import annotations

import json

import azure.functions as func


def build_openapi_spec() -> dict:
    """Return the OpenAPI 3.0.3 specification for all HTTP endpoints.

    Describes the four HTTP-triggered Azure Functions:
    - POST /api/process-response
    - POST /api/register-form
    - POST /api/activate-form
    - GET  /api/generate-flow
    """
    return {
        "openapi": "3.0.3",
        "info": {
            "title": "Forms to Fabric API",
            "version": "1.0.0",
            "description": (
                "Azure Functions API for the Microsoft Forms → Microsoft Fabric "
                "data pipeline. Handles form registration, IT approval, response "
                "processing, and Power Automate flow generation."
            ),
            "contact": {
                "name": "Forms to Fabric",
                "url": "https://github.com/michaelhuot-msft/forms-to-fabric",
            },
            "license": {
                "name": "MIT",
                "url": "https://opensource.org/licenses/MIT",
            },
        },
        "servers": [
            {
                "url": "https://{functionApp}.azurewebsites.net/api",
                "description": "Azure Functions App",
                "variables": {
                    "functionApp": {
                        "default": "your-function-app",
                        "description": "The name of your Azure Function App",
                    }
                },
            }
        ],
        "security": [{"FunctionKey": []}],
        "tags": [
            {
                "name": "Pipeline",
                "description": "Form response ingestion and processing",
            },
            {
                "name": "Registry",
                "description": "Form registration and lifecycle management",
            },
            {
                "name": "Integration",
                "description": "Power Automate flow generation",
            },
        ],
        "components": {
            "securitySchemes": {
                "FunctionKey": {
                    "type": "apiKey",
                    "in": "header",
                    "name": "x-functions-key",
                    "description": "Azure Function App host or function key",
                },
                "FunctionKeyQuery": {
                    "type": "apiKey",
                    "in": "query",
                    "name": "code",
                    "description": "Azure Function App key passed as query parameter",
                },
            },
            "schemas": {
                "Answer": {
                    "type": "object",
                    "description": "A single answer within a form response",
                    "required": ["question_id", "question", "answer"],
                    "properties": {
                        "question_id": {
                            "type": "string",
                            "description": "Question identifier (e.g. 'q1', 'q2')",
                            "example": "q1",
                        },
                        "question": {
                            "type": "string",
                            "description": "Question display text",
                            "example": "Patient Name",
                        },
                        "answer": {
                            "type": "string",
                            "description": "The response value",
                            "example": "John Doe",
                        },
                    },
                },
                "FormResponse": {
                    "type": "object",
                    "description": (
                        "Incoming payload from Power Automate containing a "
                        "Microsoft Forms response. Supports structured answers "
                        "or a raw Power Automate 'Get response details' passthrough."
                    ),
                    "required": ["form_id"],
                    "properties": {
                        "form_id": {
                            "type": "string",
                            "description": "Unique identifier for the form",
                            "example": "patient-satisfaction-001",
                        },
                        "response_id": {
                            "type": "string",
                            "description": "Unique identifier for the response",
                            "example": "r-abc123",
                        },
                        "submitted_at": {
                            "type": "string",
                            "format": "date-time",
                            "nullable": True,
                            "description": "ISO 8601 submission timestamp",
                            "example": "2024-01-15T10:30:00Z",
                        },
                        "respondent_email": {
                            "type": "string",
                            "format": "email",
                            "description": "Email address of the respondent",
                            "example": "user@contoso.com",
                        },
                        "answers": {
                            "type": "array",
                            "items": {"$ref": "#/components/schemas/Answer"},
                            "description": (
                                "Structured answers array. Used when sending "
                                "pre-parsed question/answer pairs."
                            ),
                        },
                        "raw_response": {
                            "type": "object",
                            "nullable": True,
                            "additionalProperties": True,
                            "description": (
                                "Raw 'Get response details' output from Power Automate. "
                                "If provided, answers are extracted automatically using "
                                "the form registry field mappings."
                            ),
                        },
                    },
                },
                "ProcessingResult": {
                    "type": "object",
                    "description": "Result returned after processing a single form response",
                    "required": ["status", "response_id", "form_id"],
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["success", "error"],
                            "description": "Processing outcome",
                        },
                        "response_id": {
                            "type": "string",
                            "description": "Identifier of the processed response",
                            "example": "r-abc123",
                        },
                        "form_id": {
                            "type": "string",
                            "description": "Identifier of the form",
                            "example": "patient-satisfaction-001",
                        },
                        "raw_path": {
                            "type": "string",
                            "nullable": True,
                            "description": "ABFSS path to the raw layer Parquet file",
                            "example": (
                                "abfss://raw@onelake.dfs.fabric.microsoft.com"
                                "/patient_satisfaction/r-abc123.parquet"
                            ),
                        },
                        "curated_path": {
                            "type": "string",
                            "nullable": True,
                            "description": (
                                "ABFSS path to the curated (de-identified) layer "
                                "Parquet file. Only present when the form has PHI fields."
                            ),
                            "example": (
                                "abfss://curated@onelake.dfs.fabric.microsoft.com"
                                "/patient_satisfaction/r-abc123.parquet"
                            ),
                        },
                        "message": {
                            "type": "string",
                            "nullable": True,
                            "description": (
                                "Human-readable status message or error description"
                            ),
                        },
                    },
                },
                "RegisterFormRequest": {
                    "type": "object",
                    "description": "Request body for registering a new Microsoft Form",
                    "required": ["form_url", "has_phi"],
                    "properties": {
                        "form_url": {
                            "type": "string",
                            "format": "uri",
                            "description": "Microsoft Forms URL",
                            "example": "https://forms.office.com/r/abc123XyZ",
                        },
                        "description": {
                            "type": "string",
                            "description": (
                                "Optional human-readable display name for the form "
                                "(max 50 characters; truncated if longer)"
                            ),
                            "example": "Patient Satisfaction Survey",
                        },
                        "has_phi": {
                            "oneOf": [
                                {"type": "boolean"},
                                {
                                    "type": "string",
                                    "enum": [
                                        "true",
                                        "false",
                                        "True",
                                        "False",
                                        "Yes",
                                        "No",
                                    ],
                                },
                            ],
                            "description": (
                                "Whether the form collects Protected Health Information "
                                "(PHI). PHI forms are set to 'pending_review' and require "
                                "IT approval before processing."
                            ),
                            "example": True,
                        },
                    },
                },
                "RegisterFormResponse": {
                    "type": "object",
                    "description": "Result of a successful form registration",
                    "properties": {
                        "form_id": {
                            "type": "string",
                            "description": (
                                "Unique form identifier extracted from the Forms URL"
                            ),
                            "example": "abc123XyZ",
                        },
                        "form_name": {
                            "type": "string",
                            "description": "Display name for the form",
                            "example": "Patient Satisfaction Survey",
                        },
                        "target_table": {
                            "type": "string",
                            "description": "Fabric Lakehouse target table name (lowercase + underscores)",
                            "example": "patient_satisfaction",
                        },
                        "status": {
                            "type": "string",
                            "enum": ["active", "pending_review"],
                            "description": (
                                "'active' for non-PHI forms (auto-activated); "
                                "'pending_review' for PHI forms pending IT approval"
                            ),
                        },
                        "field_count": {
                            "type": "integer",
                            "description": "Number of registered form fields",
                            "example": 0,
                        },
                        "generate_flow_url": {
                            "type": "string",
                            "description": (
                                "Relative URL to retrieve the Power Automate flow definition"
                            ),
                            "example": "/api/generate-flow?form_id=abc123XyZ",
                        },
                        "flow_create_body": {
                            "type": "object",
                            "description": (
                                "Complete Power Automate flow creation payload, ready to POST "
                                "to the PA REST API at "
                                "POST /providers/Microsoft.ProcessSimple/environments/{env}"
                                "/flows?api-version=2016-11-01"
                            ),
                        },
                    },
                },
                "AlreadyRegisteredResponse": {
                    "type": "object",
                    "description": "Returned when a form URL is already registered",
                    "properties": {
                        "status": {
                            "type": "string",
                            "enum": ["already_registered"],
                        },
                        "message": {
                            "type": "string",
                            "example": "This form is already connected to the analytics pipeline.",
                        },
                        "form_id": {"type": "string", "example": "abc123XyZ"},
                        "form_name": {
                            "type": "string",
                            "example": "Patient Satisfaction Survey",
                        },
                        "target_table": {
                            "type": "string",
                            "example": "patient_satisfaction",
                        },
                    },
                },
                "ActivateFormRequest": {
                    "type": "object",
                    "description": "Request body to activate a pending form",
                    "required": ["form_id"],
                    "properties": {
                        "form_id": {
                            "type": "string",
                            "description": "Identifier of the form to activate",
                            "example": "abc123XyZ",
                        }
                    },
                },
                "ActivateFormResponse": {
                    "type": "object",
                    "description": "Result of an activate-form request",
                    "properties": {
                        "form_id": {"type": "string", "example": "abc123XyZ"},
                        "status": {
                            "type": "string",
                            "enum": ["active"],
                        },
                        "message": {
                            "type": "string",
                            "example": "Form activated successfully",
                        },
                    },
                },
                "ErrorResponse": {
                    "type": "object",
                    "description": "Standard error response body",
                    "properties": {
                        "error": {
                            "type": "string",
                            "description": "Human-readable error message",
                            "example": "Missing required field: form_url",
                        }
                    },
                },
            },
        },
        "paths": {
            "/process-response": {
                "post": {
                    "operationId": "processFormResponse",
                    "summary": "Process a form submission",
                    "description": (
                        "Receives a Microsoft Forms response from Power Automate, "
                        "validates it against the form registry, applies de-identification "
                        "rules per field configuration, and writes the result to Microsoft "
                        "Fabric OneLake. Two layers are written: a raw layer that contains "
                        "all fields including PHI (restricted access), and a curated layer "
                        "that contains only de-identified fields (broader access)."
                    ),
                    "tags": ["Pipeline"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {"$ref": "#/components/schemas/FormResponse"},
                                "examples": {
                                    "structured": {
                                        "summary": "Structured answers array",
                                        "value": {
                                            "form_id": "patient-satisfaction-001",
                                            "response_id": "r-abc123",
                                            "submitted_at": "2024-01-15T10:30:00Z",
                                            "respondent_email": "user@contoso.com",
                                            "answers": [
                                                {
                                                    "question_id": "q1",
                                                    "question": "Patient Name",
                                                    "answer": "John Doe",
                                                },
                                                {
                                                    "question_id": "q4",
                                                    "question": "Satisfaction Rating",
                                                    "answer": "5",
                                                },
                                            ],
                                        },
                                    },
                                    "raw_passthrough": {
                                        "summary": "Raw Power Automate passthrough",
                                        "value": {
                                            "form_id": "patient-satisfaction-001",
                                            "raw_response": {
                                                "responder": "user@contoso.com",
                                                "submitDate": "2024-01-15T10:30:00Z",
                                                "answers": [
                                                    {
                                                        "questionId": "q1",
                                                        "answer": "John Doe",
                                                    }
                                                ],
                                            },
                                        },
                                    },
                                },
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Response processed and written to OneLake successfully",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ProcessingResult"
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": (
                                "Invalid JSON body, Pydantic validation error, "
                                "or empty answers array"
                            ),
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ProcessingResult"
                                    }
                                }
                            },
                        },
                        "403": {
                            "description": "Form exists but is not in 'active' status",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ProcessingResult"
                                    }
                                }
                            },
                        },
                        "404": {
                            "description": "form_id not found in registry",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ProcessingResult"
                                    }
                                }
                            },
                        },
                        "502": {
                            "description": "OneLake write failed",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ProcessingResult"
                                    }
                                }
                            },
                        },
                        "503": {
                            "description": "Fabric capacity unavailable or paused",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ProcessingResult"
                                    }
                                }
                            },
                        },
                    },
                }
            },
            "/register-form": {
                "post": {
                    "operationId": "registerForm",
                    "summary": "Register a new Microsoft Form",
                    "description": (
                        "Self-service endpoint that adds a Microsoft Form to the pipeline "
                        "registry. Non-PHI forms are auto-activated immediately. PHI forms "
                        "are set to 'pending_review' and must be approved by IT via the "
                        "activate-form endpoint after configuring de-identification methods "
                        "in the registry. Returns the form entry and a ready-to-use Power "
                        "Automate flow creation payload."
                    ),
                    "tags": ["Registry"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/RegisterFormRequest"
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Form registered, or already registered",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "oneOf": [
                                            {
                                                "$ref": "#/components/schemas/RegisterFormResponse"
                                            },
                                            {
                                                "$ref": "#/components/schemas/AlreadyRegisteredResponse"
                                            },
                                        ]
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": (
                                "Missing required fields or invalid/unrecognised form URL"
                            ),
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ErrorResponse"
                                    }
                                }
                            },
                        },
                    },
                }
            },
            "/activate-form": {
                "post": {
                    "operationId": "activateForm",
                    "summary": "Activate a pending form after IT review",
                    "description": (
                        "IT approval endpoint that transitions a form from "
                        "'pending_review' to 'active' status. Before activating, validates "
                        "that every PHI field has a de-identification method configured "
                        "('hash', 'redact', or 'generalize'). Returns a no-op 200 if the "
                        "form is already active. Inactive forms cannot be re-activated."
                    ),
                    "tags": ["Registry"],
                    "requestBody": {
                        "required": True,
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": "#/components/schemas/ActivateFormRequest"
                                }
                            }
                        },
                    },
                    "responses": {
                        "200": {
                            "description": "Form activated, or already active (idempotent)",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ActivateFormResponse"
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": (
                                "PHI fields are missing deid_method, form is inactive, "
                                "or request body is invalid"
                            ),
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ErrorResponse"
                                    }
                                }
                            },
                        },
                        "404": {
                            "description": "form_id not found in registry",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ErrorResponse"
                                    }
                                }
                            },
                        },
                    },
                }
            },
            "/generate-flow": {
                "get": {
                    "operationId": "generateFlow",
                    "summary": "Get a Power Automate flow definition for a registered form",
                    "description": (
                        "Returns a complete, importable Power Automate flow definition for "
                        "the specified registered form. The returned JSON follows the Logic "
                        "Apps workflow definition schema and can be posted directly to the "
                        "Power Automate REST API to create a new cloud flow."
                    ),
                    "tags": ["Integration"],
                    "parameters": [
                        {
                            "name": "form_id",
                            "in": "query",
                            "required": True,
                            "schema": {"type": "string"},
                            "description": "Identifier of the registered form",
                            "example": "patient-satisfaction-001",
                        },
                        {
                            "name": "function_app_url",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string", "format": "uri"},
                            "description": (
                                "Base URL of this Function App. Defaults to the "
                                "FUNCTION_APP_URL environment variable."
                            ),
                            "example": "https://my-func.azurewebsites.net",
                        },
                        {
                            "name": "key_vault_name",
                            "in": "query",
                            "required": False,
                            "schema": {"type": "string"},
                            "description": (
                                "Azure Key Vault name used to store the function key. "
                                "Defaults to the KEY_VAULT_NAME environment variable."
                            ),
                            "example": "my-keyvault",
                        },
                    ],
                    "responses": {
                        "200": {
                            "description": "Power Automate flow definition",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "type": "object",
                                        "description": (
                                            "Power Automate flow definition in the Logic Apps "
                                            "workflow definition schema "
                                            "(https://schema.management.azure.com/providers/"
                                            "Microsoft.Logic/schemas/2016-06-01/"
                                            "workflowdefinition.json#)"
                                        ),
                                    }
                                }
                            },
                        },
                        "400": {
                            "description": "Missing required form_id query parameter",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ErrorResponse"
                                    }
                                }
                            },
                        },
                        "404": {
                            "description": "form_id not found in registry",
                            "content": {
                                "application/json": {
                                    "schema": {
                                        "$ref": "#/components/schemas/ErrorResponse"
                                    }
                                }
                            },
                        },
                    },
                }
            },
        },
    }


def handle_openapi_spec(req: func.HttpRequest) -> func.HttpResponse:
    """HTTP handler: return the OpenAPI 3.0.3 specification as JSON.

    The spec is built dynamically on each request so it always reflects
    the current state of the handler modules.
    """
    spec = build_openapi_spec()
    return func.HttpResponse(
        json.dumps(spec, indent=2),
        status_code=200,
        mimetype="application/json",
        headers={"Access-Control-Allow-Origin": "*"},
    )
