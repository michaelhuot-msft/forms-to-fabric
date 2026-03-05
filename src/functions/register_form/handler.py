"""Handler for the register-form HTTP endpoint."""

from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import azure.functions as func

from shared.config import _registry_path, get_form_config, invalidate_cache
from shared.graph_client import FormNotFoundError, GraphAPIError, GraphClient
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

    form_url = body.get("form_url")
    has_phi = body.get("has_phi")

    if not form_url:
        return func.HttpResponse(
            json.dumps({"error": "Missing required field: form_url"}),
            status_code=400,
            mimetype="application/json",
        )
    if has_phi is None:
        return func.HttpResponse(
            json.dumps({"error": "Missing required field: has_phi"}),
            status_code=400,
            mimetype="application/json",
        )

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

    # Fetch form metadata and questions from Graph API
    try:
        graph = GraphClient()
        metadata = graph.get_form_metadata(form_id)
        questions = graph.get_form_questions(form_id)
    except FormNotFoundError:
        return func.HttpResponse(
            json.dumps({"error": f"Form '{form_id}' not found in Graph API"}),
            status_code=404,
            mimetype="application/json",
        )
    except (GraphAPIError, Exception) as exc:
        logger.exception("Graph API failure while registering form %s", form_id)
        return func.HttpResponse(
            json.dumps({"error": f"Graph API failure: {exc}"}),
            status_code=502,
            mimetype="application/json",
        )

    # Derive form_name and target_table
    form_name = metadata.get("title") or form_id
    target_table = _slugify(form_name)

    # Build field entries from questions
    fields = [
        FieldConfig(
            question_id=q["id"],
            field_name=_slugify(q["title"]),
            contains_phi=False,
            deid_method=None,
        )
        for q in questions
    ]

    # Determine status
    status = "pending_review" if has_phi else "active"

    form_config = FormConfig(
        form_id=form_id,
        form_name=form_name,
        target_table=target_table,
        status=status,
        fields=fields,
    )

    # Load, modify, and save the registry
    registry_path = Path(_registry_path())
    with open(registry_path, encoding="utf-8") as fh:
        registry_data = json.load(fh)

    registry_data.setdefault("forms", []).append(
        json.loads(form_config.model_dump_json())
    )

    with open(registry_path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(registry_data, fh, indent=2)
        fh.write("\n")

    # Invalidate the config cache so subsequent reads pick up the new entry
    invalidate_cache()

    logger.info(
        "Registered form %s (%s) with %d fields, status=%s",
        form_id,
        form_name,
        len(fields),
        status,
    )

    return func.HttpResponse(
        json.dumps(
            {
                "form_id": form_id,
                "form_name": form_name,
                "target_table": target_table,
                "status": status,
                "field_count": len(fields),
            }
        ),
        status_code=200,
        mimetype="application/json",
    )
