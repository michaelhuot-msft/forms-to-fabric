"""Power Automate Flow Management API client.

Creates data pipeline flows via the Flow REST API after form registration.
"""

from __future__ import annotations

import logging
import os

import requests
from azure.identity import DefaultAzureCredential

logger = logging.getLogger(__name__)

_FLOW_API_BASE = "https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple"


def _get_flow_token() -> str:
    """Get a bearer token for the Flow Management API."""
    credential = DefaultAzureCredential()
    token = credential.get_token("https://service.flow.microsoft.com/.default")
    return token.token


def _get_environment_id() -> str:
    """Get the Power Platform environment ID."""
    env_id = os.environ.get("POWER_PLATFORM_ENVIRONMENT_ID")
    if env_id:
        return env_id

    # Auto-discover: list environments and use the first one
    token = _get_flow_token()
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    resp = requests.get(f"{_FLOW_API_BASE}/environments", headers=headers, timeout=30)
    resp.raise_for_status()
    envs = resp.json().get("value", [])
    if not envs:
        raise RuntimeError("No Power Platform environments found")
    return envs[0]["name"]


def create_data_pipeline_flow(
    flow_definition: dict,
    display_name: str,
) -> dict:
    """Create a Power Automate flow via the Flow Management REST API.

    Parameters
    ----------
    flow_definition:
        The workflow definition dict (from generate_flow_definition).
    display_name:
        Display name for the new flow (e.g., "Forms to Fabric — Patient Survey").

    Returns
    -------
    dict
        The created flow metadata including flow ID and state.

    Raises
    ------
    RuntimeError
        If flow creation fails.
    """
    env_id = _get_environment_id()
    token = _get_flow_token()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }

    body = {
        "properties": {
            "displayName": display_name,
            "definition": flow_definition,
            "state": "Started",
        }
    }

    url = f"{_FLOW_API_BASE}/environments/{env_id}/flows"
    logger.info("Creating flow '%s' in environment %s", display_name, env_id)

    resp = requests.post(url, json=body, headers=headers, timeout=60)

    if resp.status_code in (200, 201):
        created = resp.json()
        flow_id = created.get("name", "unknown")
        logger.info("Flow created: %s (ID: %s)", display_name, flow_id)
        return {
            "flow_id": flow_id,
            "display_name": display_name,
            "state": created.get("properties", {}).get("state", "unknown"),
        }
    else:
        error_detail = resp.text[:500]
        logger.error(
            "Failed to create flow '%s': HTTP %d — %s",
            display_name,
            resp.status_code,
            error_detail,
        )
        raise RuntimeError(
            f"Flow creation failed (HTTP {resp.status_code}): {error_detail}"
        )
