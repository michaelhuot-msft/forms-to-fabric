#!/usr/bin/env python3
"""Rotate an Azure Function host key and store it in Key Vault.

Usage:
    python scripts/rotate_function_key.py \
        --function-app <name> \
        --resource-group <rg> \
        --key-vault <vault> \
        [--dry-run]

The script generates a new host key named ``power-automate-YYYY-MM-DD``,
stores it in Key Vault as the secret ``function-app-key``, and prints the
name of the previous key so an admin can delete it after verification.
"""

from __future__ import annotations

import argparse
import logging
import sys
from datetime import datetime, timezone

from azure.identity import DefaultAzureCredential
from azure.keyvault.secrets import SecretClient
from azure.mgmt.resource.subscriptions import SubscriptionClient
from azure.mgmt.web import WebSiteManagementClient
from azure.mgmt.web.models import KeyInfo

logger = logging.getLogger("rotate_function_key")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Rotate an Azure Function host key and store it in Key Vault.",
    )
    parser.add_argument(
        "--function-app",
        required=True,
        help="Name of the Azure Function App.",
    )
    parser.add_argument(
        "--resource-group",
        required=True,
        help="Resource group containing the Function App.",
    )
    parser.add_argument(
        "--key-vault",
        required=True,
        help="Name of the Key Vault to store the new key.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Preview actions without making changes.",
    )
    return parser.parse_args(argv)


def _get_subscription_id(credential: DefaultAzureCredential) -> str:
    """Resolve the current Azure subscription from the environment."""
    sub_client = SubscriptionClient(credential)
    subscription = next(sub_client.subscriptions.list())
    return subscription.subscription_id


def _list_existing_keys(
    web_client: WebSiteManagementClient,
    resource_group: str,
    function_app: str,
) -> dict[str, str]:
    """Return a mapping of existing host key names to their values."""
    host_keys = web_client.web_apps.list_host_keys(resource_group, function_app)
    return dict(host_keys.function_keys or {})


def rotate(
    function_app: str,
    resource_group: str,
    key_vault: str,
    *,
    dry_run: bool = False,
    credential: DefaultAzureCredential | None = None,
) -> None:
    """Perform the key rotation."""
    credential = credential or DefaultAzureCredential()

    # --- Resolve subscription ------------------------------------------
    logger.info("Resolving Azure subscription…")
    subscription_id = _get_subscription_id(credential)
    logger.info("Using subscription %s", subscription_id)

    web_client = WebSiteManagementClient(credential, subscription_id)

    # --- Discover existing keys ----------------------------------------
    logger.info(
        "Listing existing host keys for %s/%s…", resource_group, function_app
    )
    try:
        existing_keys = _list_existing_keys(web_client, resource_group, function_app)
    except Exception as exc:
        logger.error(
            "Failed to list keys for Function App '%s' in resource group '%s': %s",
            function_app,
            resource_group,
            exc,
        )
        raise SystemExit(1) from exc

    old_pa_keys = sorted(
        k for k in existing_keys if k.startswith("power-automate-")
    )
    if old_pa_keys:
        logger.info("Previous Power Automate key(s): %s", ", ".join(old_pa_keys))
    else:
        logger.info("No previous power-automate-* keys found.")

    # --- Generate new key name -----------------------------------------
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    new_key_name = f"power-automate-{today}"
    logger.info("New key name: %s", new_key_name)

    if dry_run:
        logger.info("[DRY RUN] Would create host key '%s'.", new_key_name)
        logger.info("[DRY RUN] Would store it in Key Vault '%s' as 'function-app-key'.", key_vault)
        if old_pa_keys:
            logger.info(
                "[DRY RUN] Old key(s) to clean up manually: %s",
                ", ".join(old_pa_keys),
            )
        print("\n✅ Dry run complete — no changes made.")
        return

    # --- Create / overwrite host key -----------------------------------
    logger.info("Creating host key '%s' on %s…", new_key_name, function_app)
    key_info = KeyInfo(name=new_key_name, value=None)  # None = Azure generates value
    web_client.web_apps.create_or_update_host_secret(
        resource_group,
        function_app,
        "default",
        new_key_name,
        key_info,
    )

    # Re-fetch keys to obtain the generated value
    refreshed_keys = _list_existing_keys(web_client, resource_group, function_app)
    new_key_value = refreshed_keys.get(new_key_name)
    if not new_key_value:
        logger.error("Key '%s' was created but could not be retrieved.", new_key_name)
        raise SystemExit(1)

    logger.info("Host key '%s' created successfully.", new_key_name)

    # --- Store in Key Vault --------------------------------------------
    vault_url = f"https://{key_vault}.vault.azure.net"
    secret_client = SecretClient(vault_url=vault_url, credential=credential)

    logger.info("Storing new key in Key Vault '%s' as 'function-app-key'…", key_vault)
    secret_client.set_secret(
        "function-app-key",
        new_key_value,
        content_type="Function App host key for Power Automate",
    )
    logger.info("Key Vault secret 'function-app-key' updated.")

    # --- Summary -------------------------------------------------------
    print("\n✅ Key rotation complete.")
    print(f"   New key name : {new_key_name}")
    print(f"   Key Vault    : {key_vault}")
    print(f"   Secret name  : function-app-key")
    if old_pa_keys:
        print(f"\n⚠️  Old key(s) to clean up after verification:")
        for k in old_pa_keys:
            print(f"     - {k}")
        print(
            "   Delete old keys via Azure Portal → Function App → App keys "
            "once you have confirmed the new key works."
        )


def main(argv: list[str] | None = None) -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(message)s",
        datefmt="%H:%M:%S",
    )
    args = parse_args(argv)
    rotate(
        function_app=args.function_app,
        resource_group=args.resource_group,
        key_vault=args.key_vault,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
