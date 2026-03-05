"""Core HTTP handler for the Forms to Fabric pipeline.

Receives POST requests from Power Automate, validates the payload,
optionally de-identifies PHI fields, and writes results to OneLake.
"""

from __future__ import annotations

import logging
from typing import Any

import azure.functions as func
from pydantic import ValidationError

from shared.config import get_form_config
from shared.deid import apply_deid
from shared.models import FormResponse, ProcessingResult
from shared.onelake import write_to_lakehouse

logger = logging.getLogger(__name__)


def handle_form_response(req: func.HttpRequest) -> func.HttpResponse:
    """Process an incoming form response and persist it to OneLake.

    Returns an ``HttpResponse`` with a JSON body containing the
    :class:`ProcessingResult`.
    """
    # --- Parse request body ---------------------------------------------------
    try:
        body: dict[str, Any] = req.get_json()
    except ValueError:
        return _error_response("Invalid JSON in request body", status_code=400)

    # --- Validate with Pydantic -----------------------------------------------
    try:
        form_response = FormResponse(**body)
    except ValidationError as exc:
        return _error_response(
            f"Payload validation failed: {exc.error_count()} error(s) — {exc.errors()}",
            status_code=400,
        )

    if not form_response.answers:
        return _error_response(
            "answers array must not be empty",
            status_code=400,
            form_id=form_response.form_id,
            response_id=form_response.response_id,
        )

    # --- Lookup form configuration --------------------------------------------
    form_config = get_form_config(form_response.form_id)
    if form_config is None:
        return _error_response(
            f"Unknown form_id: {form_response.form_id}",
            status_code=404,
            form_id=form_response.form_id,
            response_id=form_response.response_id,
        )

    # --- Reject non-active forms ----------------------------------------------
    if form_config.status != "active":
        return _error_response(
            f"Form '{form_response.form_id}' is not active (status: {form_config.status})",
            status_code=403,
            form_id=form_response.form_id,
            response_id=form_response.response_id,
        )

    # --- De-identification ----------------------------------------------------
    raw_records, deid_records = apply_deid(form_response.answers, form_config.fields)

    # --- Quarantine unregistered fields ---------------------------------------
    registered_qids = {f.question_id for f in form_config.fields}
    curated_records = []
    for i, ans in enumerate(form_response.answers):
        if ans.question_id in registered_qids:
            curated_records.append(deid_records[i])
        else:
            logger.warning(
                "Unregistered field '%s' in form '%s' — included in raw layer, excluded from curated",
                ans.question_id,
                form_response.form_id,
            )

    has_phi = any(f.contains_phi for f in form_config.fields)

    # --- Build data payloads for OneLake --------------------------------------
    base_meta = {
        "response_id": form_response.response_id,
        "submitted_at": form_response.submitted_at.isoformat(),
        "respondent_email": form_response.respondent_email,
    }

    raw_data = {**base_meta, "fields": raw_records}
    curated_data = {**base_meta, "fields": curated_records}

    # --- Write to OneLake -----------------------------------------------------
    try:
        raw_path = write_to_lakehouse(
            data=raw_data,
            table_name=form_config.target_table,
            layer="raw",
        )
        curated_path: str | None = None
        if has_phi:
            curated_path = write_to_lakehouse(
                data=curated_data,
                table_name=form_config.target_table,
                layer="curated",
            )
    except RuntimeError as exc:
        logger.exception("OneLake write failed")
        return _error_response(
            str(exc),
            status_code=502,
            form_id=form_response.form_id,
            response_id=form_response.response_id,
        )

    # --- Success response -----------------------------------------------------
    result = ProcessingResult(
        status="success",
        response_id=form_response.response_id,
        form_id=form_response.form_id,
        raw_path=raw_path,
        curated_path=curated_path,
        message="Response processed successfully",
    )
    return func.HttpResponse(
        body=result.model_dump_json(),
        status_code=200,
        mimetype="application/json",
    )


def _error_response(
    message: str,
    *,
    status_code: int = 400,
    form_id: str = "",
    response_id: str = "",
) -> func.HttpResponse:
    """Build a JSON error response."""
    result = ProcessingResult(
        status="error",
        response_id=response_id,
        form_id=form_id,
        message=message,
    )
    return func.HttpResponse(
        body=result.model_dump_json(),
        status_code=status_code,
        mimetype="application/json",
    )
