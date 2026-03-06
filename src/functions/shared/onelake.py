"""OneLake writer for the Forms to Fabric pipeline.

Writes Delta Lake format to the Lakehouse Tables directory so data
appears as managed tables in Fabric.
"""

from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any

import pyarrow as pa
from azure.identity import DefaultAzureCredential
from deltalake import write_deltalake

logger = logging.getLogger(__name__)


def _get_storage_options() -> dict[str, str]:
    """Build storage options for deltalake using managed identity."""
    credential = DefaultAzureCredential()
    token = credential.get_token("https://storage.azure.com/.default")
    return {
        "bearer_token": token.token,
        "use_fabric_endpoint": "true",
    }


def _get_table_uri(table_name: str, layer: str) -> str:
    """Build the OneLake URI for a Delta table.

    Pattern::

        abfss://{workspace}@onelake.dfs.fabric.microsoft.com/{lakehouse}/Tables/{table_name}_{layer}
    """
    workspace = os.environ["ONELAKE_WORKSPACE"]
    lakehouse = os.environ["ONELAKE_LAKEHOUSE"]
    return (
        f"abfss://{workspace}@onelake.dfs.fabric.microsoft.com"
        f"/{lakehouse}/Tables/{table_name}_{layer}"
    )


def write_to_lakehouse(
    data: dict[str, Any],
    table_name: str,
    layer: str,
) -> str:
    """Write a single processed response to OneLake as a Delta table row.

    Parameters
    ----------
    data:
        Dict containing ``response_id``, ``submitted_at``, ``respondent_email``,
        and ``fields`` (list of {field_name, value} dicts).
    table_name:
        Lakehouse table name (from form config).
    layer:
        ``"raw"`` or ``"curated"``.

    Returns
    -------
    str
        The Delta table URI.

    Raises
    ------
    RuntimeError
        If the write fails.
    """
    response_id: str = data["response_id"]

    # Serialize all fields as a JSON string — stable schema across all responses
    import json as _json
    import uuid

    fields_json = _json.dumps(data.get("fields", []))

    # Use a UUID if response_id is empty or a memory-address fallback
    if not response_id or response_id.startswith("raw-"):
        response_id = str(uuid.uuid4())

    row: dict[str, str] = {
        "response_id": response_id,
        "form_id": data.get("form_id", ""),
        "submitted_at": str(data.get("submitted_at", "")),
        "respondent_email": str(data.get("respondent_email", "")),
        "ingested_at": datetime.now(timezone.utc).isoformat(),
        "fields_json": fields_json,
    }

    # Build PyArrow table (all string columns for simplicity)
    table = pa.table({k: [v] for k, v in row.items()})

    table_uri = _get_table_uri(table_name, layer)
    storage_options = _get_storage_options()

    try:
        write_deltalake(
            table_uri,
            table,
            mode="append",
            schema_mode="merge",
            storage_options=storage_options,
        )
        logger.info("Wrote Delta row to %s (response_id=%s)", table_uri, response_id)
        return table_uri
    except Exception as exc:
        logger.exception("Delta write failed for %s", table_uri)
        raise RuntimeError(f"Failed to write to Delta table: {exc}") from exc
