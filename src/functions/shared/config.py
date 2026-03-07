"""Form-configuration registry reader/writer backed by Azure Blob Storage.

Uses in-memory caching with TTL. Falls back to local file for development.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from .models import FormConfig

logger = logging.getLogger(__name__)

_cache: dict[str, FormConfig] = {}
_cache_loaded_at: float = 0.0
_CACHE_TTL_SECONDS: float = 60.0  # 1 minute (shorter for blob-backed store)

# Blob storage config
_STORAGE_ACCOUNT = os.environ.get("AzureWebJobsStorage__accountName", "")
_CONTAINER_NAME = "form-registry"
_BLOB_NAME = "registry.json"


def _use_blob_storage() -> bool:
    """Return True if we should use Azure Blob Storage for the registry."""
    return bool(_STORAGE_ACCOUNT) and not os.environ.get("USE_LOCAL_REGISTRY")


def _get_blob_client():
    """Get a BlobClient for the registry blob using managed identity."""
    from azure.identity import DefaultAzureCredential
    from azure.storage.blob import BlobServiceClient

    account_url = f"https://{_STORAGE_ACCOUNT}.blob.core.windows.net"
    credential = DefaultAzureCredential()
    blob_service = BlobServiceClient(account_url, credential=credential)
    container = blob_service.get_container_client(_CONTAINER_NAME)

    # Create container if it doesn't exist
    try:
        container.get_container_properties()
    except Exception:
        try:
            container.create_container()
            logger.info("Created blob container '%s'", _CONTAINER_NAME)
        except Exception:
            pass  # May already exist or lack permissions

    return container.get_blob_client(_BLOB_NAME)


def _load_from_blob() -> dict:
    """Load registry JSON from Azure Blob Storage."""
    blob_client = _get_blob_client()
    try:
        data = blob_client.download_blob().readall()
        return json.loads(data)
    except Exception as exc:
        logger.warning("Could not load registry from blob: %s. Returning empty.", exc)
        return {"forms": []}


def _save_to_blob(registry_data: dict) -> None:
    """Save registry JSON to Azure Blob Storage."""
    from azure.storage.blob import ContentSettings

    blob_client = _get_blob_client()
    blob_client.upload_blob(
        json.dumps(registry_data, indent=2),
        overwrite=True,
        content_settings=ContentSettings(content_type="application/json"),
    )
    logger.info("Registry saved to blob storage.")


def _local_registry_path() -> str:
    """Return the path to a local form-registry JSON file (development fallback)."""
    # Check alongside the function app
    local_path = Path(__file__).resolve().parent.parent / "form-registry.json"
    if local_path.exists():
        return str(local_path)
    # Fall back to repo structure
    repo_path = Path(__file__).resolve().parents[3] / "config" / "form-registry.json"
    return str(repo_path)


def _load_from_file() -> dict:
    """Load registry JSON from local file."""
    path = _local_registry_path()
    logger.info("Loading form registry from file: %s", path)
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _save_to_file(registry_data: dict) -> None:
    """Save registry JSON to local file."""
    path = _local_registry_path()
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(registry_data, fh, indent=2)
        fh.write("\n")


def _load_registry() -> dict[str, FormConfig]:
    """Load all form configs and return a dict keyed by form_id."""
    if _use_blob_storage():
        data = _load_from_blob()
    else:
        data = _load_from_file()

    configs: dict[str, FormConfig] = {}
    for entry in data.get("forms", []):
        fc = FormConfig(**entry)
        configs[fc.form_id] = fc
    return configs


def _ensure_cache() -> None:
    """Refresh the in-memory cache if it has expired."""
    global _cache, _cache_loaded_at  # noqa: PLW0603
    now = time.time()
    if not _cache or (now - _cache_loaded_at) > _CACHE_TTL_SECONDS:
        _cache = _load_registry()
        _cache_loaded_at = now


def get_form_config(form_id: str) -> Optional[FormConfig]:
    """Look up the configuration for *form_id*.

    Returns ``None`` if the form is not registered.
    """
    _ensure_cache()
    return _cache.get(form_id)


def get_all_form_configs() -> dict[str, FormConfig]:
    """Return all registered form configurations keyed by form_id."""
    _ensure_cache()
    return dict(_cache)


def load_registry_data() -> dict:
    """Load the raw registry JSON (for read-modify-write operations)."""
    if _use_blob_storage():
        return _load_from_blob()
    return _load_from_file()


def save_registry_data(registry_data: dict) -> None:
    """Save registry JSON to the backing store."""
    if _use_blob_storage():
        _save_to_blob(registry_data)
    else:
        _save_to_file(registry_data)


def invalidate_cache() -> None:
    """Force the next ``get_form_config`` call to reload."""
    global _cache, _cache_loaded_at  # noqa: PLW0603
    _cache = {}
    _cache_loaded_at = 0.0
