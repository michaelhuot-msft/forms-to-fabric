"""OneLake (ADLS Gen2) writer for the Forms to Fabric pipeline."""

from __future__ import annotations

import io
import logging
import os
from datetime import datetime, timezone
from typing import Any

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from azure.identity import DefaultAzureCredential
from azure.storage.filedatalake import DataLakeServiceClient

logger = logging.getLogger(__name__)

_MAX_RETRIES = 3


def _get_service_client() -> DataLakeServiceClient:
    """Build an authenticated ``DataLakeServiceClient`` for OneLake."""
    account_name = os.environ["ONELAKE_ACCOUNT_NAME"]
    credential = DefaultAzureCredential()
    account_url = f"https://{account_name}.dfs.fabric.microsoft.com"
    return DataLakeServiceClient(account_url=account_url, credential=credential)


def _build_path(table_name: str, layer: str, response_id: str) -> str:
    """Construct the OneLake file path for a response.

    Pattern::

        Tables/{table_name}/{layer}/year={Y}/month={M}/day={D}/{response_id}.parquet
    """
    now = datetime.now(timezone.utc)
    return (
        f"Tables/{table_name}/{layer}"
        f"/year={now.year}/month={now.month:02d}/day={now.day:02d}"
        f"/{response_id}.parquet"
    )


def _records_to_parquet_bytes(records: list[dict[str, Any]]) -> bytes:
    """Serialize a list of flat dicts into an in-memory Parquet file."""
    df = pd.DataFrame(records)
    table = pa.Table.from_pandas(df)
    buf = io.BytesIO()
    pq.write_table(table, buf)
    return buf.getvalue()


def write_to_lakehouse(
    data: dict[str, Any],
    table_name: str,
    layer: str,
) -> str:
    """Write a single processed response to OneLake as a Parquet file.

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
        The full path of the written Parquet file.

    Raises
    ------
    RuntimeError
        If the write fails after all retry attempts.
    """
    workspace = os.environ["ONELAKE_WORKSPACE"]
    lakehouse = os.environ["ONELAKE_LAKEHOUSE"]
    response_id: str = data["response_id"]

    flat_record: dict[str, Any] = {
        "response_id": response_id,
        "submitted_at": data.get("submitted_at"),
        "respondent_email": data.get("respondent_email"),
    }
    for field in data.get("fields", []):
        flat_record[field["field_name"]] = field["value"]

    parquet_bytes = _records_to_parquet_bytes([flat_record])
    file_path = _build_path(table_name, layer, response_id)

    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            service_client = _get_service_client()
            fs_client = service_client.get_file_system_client(workspace)
            dir_path = file_path.rsplit("/", 1)[0]
            dir_client = fs_client.get_directory_client(f"{lakehouse}/{dir_path}")
            dir_client.create_directory()

            file_client = dir_client.get_file_client(f"{response_id}.parquet")
            file_client.upload_data(parquet_bytes, overwrite=True)

            logger.info("Wrote %s/%s (attempt %d)", lakehouse, file_path, attempt)
            return f"{lakehouse}/{file_path}"
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            logger.warning(
                "OneLake write attempt %d/%d failed: %s", attempt, _MAX_RETRIES, exc
            )

    raise RuntimeError(
        f"Failed to write to OneLake after {_MAX_RETRIES} attempts"
    ) from last_exc
