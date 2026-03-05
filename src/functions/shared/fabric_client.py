"""Fabric REST API client for workspace role-assignment auditing."""

from __future__ import annotations

import logging
import os
import time
from typing import Any

import httpx
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

_FABRIC_SCOPE = "https://api.fabric.microsoft.com/.default"
_DEFAULT_BASE_URL = "https://api.fabric.microsoft.com/v1"
_MAX_RETRIES = 3
_RETRY_BACKOFF = 2  # seconds, doubles each retry


def _base_url() -> str:
    return os.environ.get("FABRIC_API_BASE_URL", _DEFAULT_BASE_URL).rstrip("/")


def _workspace_id() -> str:
    wid = os.environ.get("FABRIC_WORKSPACE_ID")
    if not wid:
        raise EnvironmentError("FABRIC_WORKSPACE_ID environment variable is required")
    return wid


def _get_access_token() -> str:
    """Obtain a bearer token for the Fabric API using DefaultAzureCredential."""
    credential = DefaultAzureCredential()
    token = credential.get_token(_FABRIC_SCOPE)
    return token.token


def _request_with_retry(method: str, url: str, headers: dict[str, str]) -> dict[str, Any]:
    """Execute an HTTP request with retry logic for rate-limiting (429) responses.

    Args:
        method: HTTP method (GET, POST, etc.).
        url: Fully-qualified request URL.
        headers: Request headers including Authorization.

    Returns:
        Parsed JSON response body.

    Raises:
        httpx.HTTPStatusError: On non-retryable HTTP errors.
    """
    backoff = _RETRY_BACKOFF
    for attempt in range(1, _MAX_RETRIES + 1):
        response = httpx.request(method, url, headers=headers, timeout=30)

        if response.status_code == 429:
            retry_after = int(response.headers.get("Retry-After", backoff))
            logger.warning(
                "Rate limited by Fabric API (attempt %d/%d). Retrying in %ds.",
                attempt,
                _MAX_RETRIES,
                retry_after,
            )
            time.sleep(retry_after)
            backoff *= 2
            continue

        response.raise_for_status()
        return response.json()

    raise RuntimeError(f"Fabric API request failed after {_MAX_RETRIES} retries: {url}")


def get_workspace_users(workspace_id: str | None = None) -> list[dict[str, str]]:
    """List all role assignments for a Fabric workspace.

    Args:
        workspace_id: Workspace GUID. Falls back to FABRIC_WORKSPACE_ID env var.

    Returns:
        List of dicts with keys: principal_id, principal_type, role, display_name.

    Raises:
        EnvironmentError: If no workspace_id is provided or configured.
        httpx.HTTPStatusError: On API errors (e.g. 404 workspace not found).
    """
    wid = workspace_id or _workspace_id()
    url = f"{_base_url()}/workspaces/{wid}/roleAssignments"
    headers = {"Authorization": f"Bearer {_get_access_token()}"}

    data = _request_with_retry("GET", url, headers)

    assignments: list[dict[str, str]] = []
    for item in data.get("value", []):
        principal = item.get("principal", {})
        assignments.append(
            {
                "principal_id": principal.get("id", ""),
                "principal_type": principal.get("type", ""),
                "role": item.get("role", ""),
                "display_name": principal.get("displayName", ""),
            }
        )

    return assignments


def get_workspace_details(workspace_id: str | None = None) -> dict[str, Any]:
    """Retrieve metadata for a Fabric workspace.

    Args:
        workspace_id: Workspace GUID. Falls back to FABRIC_WORKSPACE_ID env var.

    Returns:
        Dict with workspace metadata (id, displayName, type, state, etc.).
    """
    wid = workspace_id or _workspace_id()
    url = f"{_base_url()}/workspaces/{wid}"
    headers = {"Authorization": f"Bearer {_get_access_token()}"}

    return _request_with_retry("GET", url, headers)
