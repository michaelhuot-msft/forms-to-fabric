"""Create the registration Power Automate flow via the Flow Management API.

Usage (called by Create-RegistrationFlow.ps1)::

    python scripts/create_registration_flow.py \\
        --registration-form-id "v4j5cvGGr0G..." \\
        --function-app-url "https://func-forms-dev-abc.azurewebsites.net" \\
        --function-app-key "abc123..." \\
        --flow-environment-id "Default-<tenant-id>" \\
        --alert-email "admin@contoso.com" \\
        --forms-connection "shared_microsoftforms" \\
        --outlook-connection "shared_office365" \\
        --webcontents-connection "shared_webcontents"
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

# Add src/functions to the path so we can import shared modules
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src" / "functions"))

import requests
from azure.identity import DefaultAzureCredential

from shared.registration_flow_builder import build_registration_flow_create_body

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger(__name__)

_FLOW_API_BASE = "https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple"


def _get_flow_token() -> str:
    """Get a bearer token for the Flow Management API."""
    credential = DefaultAzureCredential()
    token = credential.get_token("https://service.flow.microsoft.com/.default")
    return token.token


def create_flow(body: dict, environment_id: str) -> dict:
    """POST the flow create body to the Flow Management API.

    Returns the created flow metadata.
    """
    token = _get_flow_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    }
    url = f"{_FLOW_API_BASE}/environments/{environment_id}/flows?api-version=2016-11-01"

    logger.info("Creating registration flow in environment %s ...", environment_id)
    resp = requests.post(url, json=body, headers=headers, timeout=60)

    if resp.status_code in (200, 201):
        created = resp.json()
        flow_id = created.get("name", "unknown")
        state = created.get("properties", {}).get("state", "unknown")
        logger.info("Registration flow created successfully.")
        logger.info("  Flow ID:    %s", flow_id)
        logger.info("  State:      %s", state)
        return {"flow_id": flow_id, "state": state}
    else:
        detail = resp.text[:1000]
        logger.error("Flow creation failed (HTTP %d):\n%s", resp.status_code, detail)
        sys.exit(1)


def main() -> None:
    """Parse arguments and create the registration flow."""
    parser = argparse.ArgumentParser(
        description="Create the Forms to Fabric registration flow via Flow API."
    )
    parser.add_argument(
        "--registration-form-id", required=True, help="Registration Microsoft Form ID"
    )
    parser.add_argument(
        "--function-app-url", required=True, help="Azure Function App base URL"
    )
    parser.add_argument(
        "--function-app-key", required=True, help="Function or host key"
    )
    parser.add_argument(
        "--flow-environment-id", required=True, help="Power Platform environment ID"
    )
    parser.add_argument("--alert-email", required=True, help="Admin notification email")
    parser.add_argument(
        "--forms-connection",
        default="shared_microsoftforms",
        help="Microsoft Forms connection name",
    )
    parser.add_argument(
        "--outlook-connection",
        default="shared_office365",
        help="Office 365 Outlook connection name",
    )
    parser.add_argument(
        "--webcontents-connection",
        default="shared_webcontents",
        help="HTTP with Microsoft Entra ID connection name",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the flow body JSON without creating the flow",
    )
    args = parser.parse_args()

    body = build_registration_flow_create_body(
        registration_form_id=args.registration_form_id,
        function_app_url=args.function_app_url,
        function_app_key=args.function_app_key,
        flow_environment_id=args.flow_environment_id,
        alert_email=args.alert_email,
        forms_connection_name=args.forms_connection,
        outlook_connection_name=args.outlook_connection,
        webcontents_connection_name=args.webcontents_connection,
    )

    if args.dry_run:
        logger.info("Dry run — flow definition:")
        print(json.dumps(body, indent=2))
        return

    result = create_flow(body, args.flow_environment_id)
    # Output flow ID for the PowerShell wrapper to capture
    print(json.dumps(result))


if __name__ == "__main__":
    main()
