"""Handler for the register-form HTTP endpoint."""

from __future__ import annotations

import json
import logging
import re
from urllib.parse import parse_qs, urlparse

import azure.functions as func

from shared.config import (
    get_form_config,
    invalidate_cache,
    load_registry_data,
    save_registry_data,
)
from shared.models import FieldConfig, FormConfig

logger = logging.getLogger(__name__)


def _extract_form_id(url: str) -> str | None:
    """Extract a form ID from a Microsoft Forms URL."""
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "id" in qs:
        return qs["id"][0]
    match = re.search(r"/r/([A-Za-z0-9_-]+)", parsed.path)
    if match:
        return match.group(1)
    return None


def _slugify(name: str) -> str:
    """Convert a display name to a valid table name (lowercase, underscores)."""
    slug = name.lower().strip()
    slug = re.sub(r"[^a-z0-9]+", "_", slug)
    slug = slug.strip("_")
    return slug or "unnamed_form"


def handle_register_form(req: func.HttpRequest) -> func.HttpResponse:
    """Register a new Microsoft Form for pipeline processing."""
    # Parse input
    try:
        body = req.get_json()
    except ValueError:
        return func.HttpResponse(
            json.dumps({"error": "Invalid JSON body"}),
            status_code=400,
            mimetype="application/json",
        )

    # Support raw_response passthrough (same pattern as process-response)
    raw_response = body.get("raw_response")
    if raw_response and isinstance(raw_response, dict):
        # Extract the 3 registration fields from raw Forms response
        # Fields are in order: form_url, description, has_phi
        metadata_keys = {
            "responder",
            "submitDate",
            "responseId",
            "@odata.context",
            "@odata.etag",
        }
        field_values = []
        for key, value in raw_response.items():
            if key in metadata_keys or key.startswith("@"):
                continue
            field_values.append(str(value) if value is not None else "")

        form_url = field_values[0] if len(field_values) > 0 else ""
        # field_values[1] is description (logged but not used for registration logic)
        has_phi_raw = field_values[2] if len(field_values) > 2 else "No"
    else:
        form_url = body.get("form_url")
        has_phi_raw = body.get("has_phi")

    if not form_url:
        return func.HttpResponse(
            json.dumps({"error": "Missing required field: form_url"}),
            status_code=400,
            mimetype="application/json",
        )
    if has_phi_raw is None:
        return func.HttpResponse(
            json.dumps({"error": "Missing required field: has_phi"}),
            status_code=400,
            mimetype="application/json",
        )

    # Normalize has_phi — accept bool, "true"/"false", "Yes"/"No"
    if isinstance(has_phi_raw, bool):
        has_phi = has_phi_raw
    elif isinstance(has_phi_raw, str):
        has_phi = has_phi_raw.lower().strip() in ("true", "yes", "1")
    else:
        has_phi = bool(has_phi_raw)

    # Extract form_id from URL
    form_id = _extract_form_id(form_url)
    if not form_id:
        return func.HttpResponse(
            json.dumps({"error": "Cannot extract form_id from URL"}),
            status_code=400,
            mimetype="application/json",
        )

    # Check for duplicates
    existing = get_form_config(form_id)
    if existing is not None:
        return func.HttpResponse(
            json.dumps({"error": f"Form '{form_id}' is already registered"}),
            status_code=409,
            mimetype="application/json",
        )

    # Derive form_name and target_table from form_id (no Graph API needed)
    form_name = form_id[:40] if len(form_id) > 40 else form_id
    target_table = _slugify(form_name)

    # Register with empty fields — they'll be auto-discovered from raw_response
    # at processing time, or manually configured via manage_registry.py
    fields: list[FieldConfig] = []

    # Determine status
    status = "pending_review" if has_phi else "active"

    form_config = FormConfig(
        form_id=form_id,
        form_name=form_name,
        target_table=target_table,
        status=status,
        fields=fields,
    )

    # Load, modify, and save the registry (blob storage or local file)
    registry_data = load_registry_data()

    registry_data.setdefault("forms", []).append(
        json.loads(form_config.model_dump_json())
    )

    save_registry_data(registry_data)

    # Invalidate the config cache so subsequent reads pick up the new entry
    invalidate_cache()

    logger.info(
        "Registered form %s (%s) with %d fields, status=%s",
        form_id,
        form_name,
        len(fields),
        status,
    )

    # --- Auto-create the data pipeline PA flow --------------------------------
    flow_result = None
    flow_error = None
    try:
        import os

        from generate_flow.handler import generate_flow_definition
        from shared.flow_api_client import create_data_pipeline_flow

        function_app_url = os.environ.get(
            "FUNCTION_APP_URL",
            f"https://{os.environ.get('WEBSITE_HOSTNAME', 'localhost')}",
        )
        key_vault_name = os.environ.get("KEY_VAULT_NAME", "")

        flow_def = generate_flow_definition(form_id, function_app_url, key_vault_name)
        flow_result = create_data_pipeline_flow(
            flow_definition=flow_def,
            display_name=f"Forms to Fabric — {form_name}",
        )
        logger.info("Auto-created data pipeline flow: %s", flow_result)
    except Exception as exc:
        flow_error = str(exc)
        logger.warning(
            "Could not auto-create data pipeline flow for %s: %s",
            form_id,
            exc,
        )

    response_body = {
        "form_id": form_id,
        "form_name": form_name,
        "target_table": target_table,
        "status": status,
        "field_count": len(fields),
        "generate_flow_url": f"/api/generate-flow?form_id={form_id}",
    }
    if flow_result:
        response_body["data_flow"] = flow_result
    if flow_error:
        response_body["data_flow_error"] = flow_error

    return func.HttpResponse(
        json.dumps(response_body),
        status_code=200,
        mimetype="application/json",
    )
