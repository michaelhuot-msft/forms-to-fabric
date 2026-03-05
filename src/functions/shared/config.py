"""Form-configuration registry reader with in-memory caching."""

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
_CACHE_TTL_SECONDS: float = 300.0  # 5 minutes


def _registry_path() -> str:
    """Return the path to the form-registry JSON file."""
    return os.environ.get(
        "FORM_REGISTRY_PATH",
        str(Path(__file__).resolve().parents[3] / "config" / "form-registry.json"),
    )


def _load_registry() -> dict[str, FormConfig]:
    """Load all form configs from the registry file and return a dict keyed by form_id."""
    path = _registry_path()
    logger.info("Loading form registry from %s", path)
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)

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

    Returns ``None`` if the form is not registered.  Results are cached in
    memory and refreshed every ``_CACHE_TTL_SECONDS`` seconds.
    """
    _ensure_cache()
    return _cache.get(form_id)


def get_all_form_configs() -> dict[str, FormConfig]:
    """Return all registered form configurations keyed by form_id.

    Results are cached in memory and refreshed every
    ``_CACHE_TTL_SECONDS`` seconds.
    """
    _ensure_cache()
    return dict(_cache)


def invalidate_cache() -> None:
    """Force the next ``get_form_config`` call to reload from disk."""
    global _cache, _cache_loaded_at  # noqa: PLW0603
    _cache = {}
    _cache_loaded_at = 0.0
