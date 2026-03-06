"""Handler for the activate-form HTTP endpoint."""

from __future__ import annotations

import json
import logging

import azure.functions as func

from shared.config import invalidate_cache, load_registry_data, save_registry_data

logger = logging.getLogger(__name__)


def handle_activate_form(req: func.HttpRequest) -> func.HttpResponse:
    """Activate a form after IT review."""
    # Parse input
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json",
        )

    form_id = body.get("form_id")
    if not form_id:
        return func.HttpResponse(
            json.dumps({"error": "Missing required field: form_id"}),
            status_code=400,
            mimetype="application/json",
        )

    # Load registry
    registry_data = load_registry_data()

    # Find the form
    form_entry = None
    for entry in registry_data.get("forms", []):
        if entry["form_id"] == form_id:
            form_entry = entry
            break

    if form_entry is None:
        return func.HttpResponse(
            json.dumps({"error": f"Form '{form_id}' not found in registry"}),
            status_code=404,
            mimetype="application/json",
        )

    current_status = form_entry.get("status", "active")

    # Already active
    if current_status == "active":
        return func.HttpResponse(
            json.dumps(
                {
                    "form_id": form_id,
                    "status": "active",
                    "message": "already active",
                }
            ),
            status_code=200,
            mimetype="application/json",
        )

    # Cannot activate inactive forms
    if current_status == "inactive":
        return func.HttpResponse(
            json.dumps({"error": "cannot activate an inactive form"}),
            status_code=400,
            mimetype="application/json",
        )

    # Validate PHI fields have deid_method configured
    unconfigured = [
        field["field_name"]
        for field in form_entry.get("fields", [])
        if field.get("contains_phi") and not field.get("deid_method")
    ]

    if unconfigured:
        return func.HttpResponse(
            json.dumps(
                {
                    "error": "PHI fields missing deid_method configuration",
                    "unconfigured_fields": unconfigured,
                }
            ),
            status_code=400,
            mimetype="application/json",
        )

    # Activate
    form_entry["status"] = "active"
    save_registry_data(registry_data)

    invalidate_cache()

    logger.info("Activated form %s", form_id)

    return func.HttpResponse(
        json.dumps(
            {
                "form_id": form_id,
                "status": "active",
                "message": "Form activated successfully",
            }
        ),
        status_code=200,
        mimetype="application/json",
    )
