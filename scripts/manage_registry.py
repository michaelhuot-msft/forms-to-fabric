#!/usr/bin/env python3
"""CLI tool for managing the form-registry.json configuration file."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_REGISTRY = REPO_ROOT / "config" / "form-registry.json"
DEFAULT_SCHEMA = REPO_ROOT / "config" / "form-registry.schema.json"

VALID_DEID_METHODS = {"hash", "redact", "generalize"}
VALID_FIELD_TYPES = {"date", "age"}

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def load_json(path: Path) -> Any:
    """Load and parse a JSON file, raising on syntax errors."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def save_registry(data: dict, path: Path) -> None:
    """Write the registry back to disk with consistent formatting."""
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        json.dump(data, f, indent=2)
        f.write("\n")


def extract_form_id(url: str) -> str | None:
    """Extract a form ID from a Microsoft Forms URL.

    Supports:
      - https://forms.office.com/Pages/DesignPageV2.aspx?id=<ID>&...
      - https://forms.office.com/Pages/ResponsePage.aspx?id=<ID>&...
      - https://forms.office.com/r/<ID>
      - https://forms.microsoft.com/r/<ID>

    Returns None if the URL doesn't match any known pattern.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "id" in qs:
        return qs["id"][0]
    match = re.search(r"/r/([A-Za-z0-9_-]+)", parsed.path)
    if match:
        return match.group(1)
    return None


def fetch_form_name(form_id: str) -> str | None:
    """Try to fetch the form title from Microsoft Graph API.

    Returns None if the API is unreachable or auth is unavailable
    (e.g. running locally without Azure credentials).
    """
    try:
        from src.functions.shared.graph_client import GraphClient
        client = GraphClient()
        meta = client.get_form_metadata(form_id)
        return meta.get("title") or None
    except Exception:
        return None


def find_form(registry: dict, form_id: str) -> dict | None:
    """Return the form entry matching *form_id*, or None."""
    for form in registry.get("forms", []):
        if form.get("form_id") == form_id:
            return form
    return None


# ---------------------------------------------------------------------------
# Schema validation (lightweight, no external deps)
# ---------------------------------------------------------------------------


def validate_registry(registry: dict, schema_path: Path | None = None) -> list[str]:
    """Validate *registry* dict and return a list of error strings."""
    errors: list[str] = []

    # Structural checks
    if not isinstance(registry, dict):
        errors.append("Root element must be a JSON object")
        return errors

    if "forms" not in registry:
        errors.append("Missing required key 'forms' at root level")
        return errors

    forms = registry["forms"]
    if not isinstance(forms, list):
        errors.append("'forms' must be an array")
        return errors

    seen_form_ids: dict[str, int] = {}

    for idx, form in enumerate(forms):
        prefix = f"forms[{idx}]"

        if not isinstance(form, dict):
            errors.append(f"{prefix}: each form must be an object")
            continue

        # Required string fields
        for key in ("form_id", "form_name", "target_table"):
            if key not in form:
                errors.append(f"{prefix}: missing required field '{key}'")
            elif not isinstance(form[key], str) or not form[key]:
                errors.append(f"{prefix}.{key}: must be a non-empty string")

        # target_table pattern
        target_table = form.get("target_table", "")
        if isinstance(target_table, str) and target_table:
            import re
            if not re.match(r"^[a-z_]+$", target_table):
                errors.append(
                    f"{prefix}.target_table: must match ^[a-z_]+$ (got '{target_table}')"
                )

        # Duplicate form_id check
        fid = form.get("form_id")
        if isinstance(fid, str) and fid:
            if fid in seen_form_ids:
                errors.append(
                    f"{prefix}.form_id: duplicate form_id '{fid}' "
                    f"(first seen at forms[{seen_form_ids[fid]}])"
                )
            else:
                seen_form_ids[fid] = idx

        # Fields
        if "fields" not in form:
            errors.append(f"{prefix}: missing required field 'fields'")
            continue

        fields = form["fields"]
        if not isinstance(fields, list):
            errors.append(f"{prefix}.fields: must be an array")
            continue

        seen_qids: dict[str, int] = {}
        for fidx, field in enumerate(fields):
            fprefix = f"{prefix}.fields[{fidx}]"

            if not isinstance(field, dict):
                errors.append(f"{fprefix}: each field must be an object")
                continue

            for key in ("question_id", "field_name"):
                if key not in field:
                    errors.append(f"{fprefix}: missing required field '{key}'")
                elif not isinstance(field[key], str) or not field[key]:
                    errors.append(f"{fprefix}.{key}: must be a non-empty string")

            # Duplicate question_id within form
            qid = field.get("question_id")
            if isinstance(qid, str) and qid:
                if qid in seen_qids:
                    errors.append(
                        f"{fprefix}.question_id: duplicate question_id '{qid}' "
                        f"within form '{fid}'"
                    )
                else:
                    seen_qids[qid] = fidx

            # contains_phi type check
            contains_phi = field.get("contains_phi")
            if contains_phi is not None and not isinstance(contains_phi, bool):
                errors.append(f"{fprefix}.contains_phi: must be a boolean")

            # deid_method validation
            deid = field.get("deid_method")
            if deid is not None and deid not in VALID_DEID_METHODS:
                errors.append(
                    f"{fprefix}.deid_method: invalid value '{deid}' "
                    f"(must be one of {sorted(VALID_DEID_METHODS)} or null)"
                )

            # field_type validation
            ftype = field.get("field_type")
            if ftype is not None and ftype not in VALID_FIELD_TYPES:
                errors.append(
                    f"{fprefix}.field_type: invalid value '{ftype}' "
                    f"(must be one of {sorted(VALID_FIELD_TYPES)} or null)"
                )

            # PHI requires deid_method
            if contains_phi is True and deid is None:
                errors.append(
                    f"{fprefix}: contains_phi is true but deid_method is null"
                )

    # Optional: validate against JSON Schema if jsonschema is installed
    if schema_path and schema_path.exists():
        try:
            import jsonschema  # type: ignore[import-untyped]

            schema = load_json(schema_path)
            validator = jsonschema.Draft7Validator(schema)
            for error in validator.iter_errors(registry):
                path_str = ".".join(str(p) for p in error.absolute_path)
                errors.append(f"Schema: {path_str}: {error.message}" if path_str else f"Schema: {error.message}")
        except ImportError:
            pass  # jsonschema not installed – skip schema-based validation

    return errors


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_validate(args: argparse.Namespace) -> int:
    registry_path: Path = args.registry
    schema_path: Path = args.schema

    # 1. Try to parse JSON
    try:
        registry = load_json(registry_path)
    except json.JSONDecodeError as exc:
        print(f"ERROR: Invalid JSON syntax in {registry_path}")
        print(f"  {exc}")
        return 1
    except FileNotFoundError:
        print(f"ERROR: Registry file not found: {registry_path}")
        return 1

    # 2. Validate
    errors = validate_registry(registry, schema_path)

    if errors:
        print(f"VALIDATION FAILED — {len(errors)} error(s):")
        for err in errors:
            print(f"  • {err}")
        return 1

    form_count = len(registry.get("forms", []))
    print(f"OK — registry is valid ({form_count} form(s))")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    try:
        registry = load_json(args.registry)
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}")
        return 1

    forms = registry.get("forms", [])
    if not forms:
        print("No forms registered.")
        return 0

    # Build table data
    headers = ["form_id", "form_name", "target_table", "fields", "phi_fields"]
    rows = []
    for form in forms:
        fields = form.get("fields", [])
        phi_count = sum(1 for f in fields if f.get("contains_phi"))
        rows.append([
            form.get("form_id", ""),
            form.get("form_name", ""),
            form.get("target_table", ""),
            str(len(fields)),
            str(phi_count),
        ])

    # Calculate column widths
    widths = [len(h) for h in headers]
    for row in rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))

    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    print(fmt.format(*headers))
    print(fmt.format(*["-" * w for w in widths]))
    for row in rows:
        print(fmt.format(*row))

    return 0


def cmd_add_form(args: argparse.Namespace) -> int:
    registry_path: Path = args.registry

    try:
        registry = load_json(registry_path)
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}")
        return 1

    # Resolve form_id: from --form-url or --form-id
    form_id: str | None = getattr(args, "form_id", None)
    form_url: str | None = getattr(args, "form_url", None)

    if form_url:
        form_id = extract_form_id(form_url)
        if not form_id:
            print("ERROR: Could not extract a form ID from this URL.")
            print()
            print("Expected URL formats:")
            print("  https://forms.office.com/Pages/DesignPageV2.aspx?id=<FORM_ID>&...")
            print("  https://forms.office.com/r/<FORM_ID>")
            print()
            print("Tip: Open the form in edit mode and copy the URL from your browser.")
            return 1
        print(f"Extracted form ID: {form_id}")

    if not form_id:
        print("ERROR: provide --form-url or --form-id")
        return 1

    if find_form(registry, form_id):
        print(f"ERROR: form_id '{form_id}' already exists")
        return 1

    # Resolve form_name: explicit flag > Graph API > form_id fallback
    form_name = getattr(args, "form_name", None)
    if not form_name:
        print("Fetching form name from Microsoft Graph API...")
        form_name = fetch_form_name(form_id)
        if form_name:
            print(f"Form name: {form_name}")
        else:
            form_name = form_id
            print(f"Could not reach Graph API — using form ID as name: {form_name}")

    new_form = {
        "form_id": form_id,
        "form_name": form_name,
        "target_table": args.target_table,
        "fields": [],
    }

    registry["forms"].append(new_form)
    save_registry(registry, registry_path)
    print(f"Added form '{form_id}' → table '{args.target_table}'")
    return 0


def cmd_add_field(args: argparse.Namespace) -> int:
    registry_path: Path = args.registry

    try:
        registry = load_json(registry_path)
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}")
        return 1

    form = find_form(registry, args.form_id)
    if form is None:
        print(f"ERROR: form_id '{args.form_id}' not found")
        return 1

    # Check duplicate question_id
    for field in form["fields"]:
        if field["question_id"] == args.question_id:
            print(
                f"ERROR: question_id '{args.question_id}' already exists "
                f"in form '{args.form_id}'"
            )
            return 1

    # Validate PHI / deid_method consistency
    if args.contains_phi and args.deid_method == "none":
        print("ERROR: --deid-method is required (not 'none') when --contains-phi is set")
        return 1

    deid_value = None if args.deid_method == "none" else args.deid_method
    field_type_value = None if args.field_type is None else args.field_type

    new_field: dict[str, Any] = {
        "question_id": args.question_id,
        "field_name": args.field_name,
        "contains_phi": args.contains_phi,
        "deid_method": deid_value,
        "field_type": field_type_value,
    }

    form["fields"].append(new_field)
    save_registry(registry, registry_path)
    print(f"Added field '{args.question_id}' to form '{args.form_id}'")
    return 0


def cmd_remove_form(args: argparse.Namespace) -> int:
    registry_path: Path = args.registry

    try:
        registry = load_json(registry_path)
    except (json.JSONDecodeError, FileNotFoundError) as exc:
        print(f"ERROR: {exc}")
        return 1

    form = find_form(registry, args.form_id)
    if form is None:
        print(f"ERROR: form_id '{args.form_id}' not found")
        return 1

    if not args.yes:
        answer = input(f"Remove form '{args.form_id}'? [y/N] ").strip().lower()
        if answer != "y":
            print("Aborted.")
            return 0

    registry["forms"] = [
        f for f in registry["forms"] if f.get("form_id") != args.form_id
    ]
    save_registry(registry, registry_path)
    print(f"Removed form '{args.form_id}'")
    return 0


def cmd_lookup_id(args: argparse.Namespace) -> int:
    """Extract the form ID from a Microsoft Forms URL.

    Supports these URL patterns:
      - https://forms.office.com/Pages/DesignPageV2.aspx?id=<FORM_ID>&...
      - https://forms.office.com/r/<FORM_ID>
      - https://forms.microsoft.com/r/<FORM_ID>
      - https://forms.office.com/Pages/ResponsePage.aspx?id=<FORM_ID>&...
    """
    url = args.url.strip()

    # Pattern 1: ?id= query parameter
    parsed = urlparse(url)
    qs = parse_qs(parsed.query)
    if "id" in qs:
        form_id = qs["id"][0]
        print(f"Form ID:  {form_id}")
        print(f"\nUse it with:")
        print(f"  python scripts/manage_registry.py add-form --form-id \"{form_id}\" --form-name \"<name>\" --target-table \"<table>\"")
        return 0

    # Pattern 2: /r/<id> short link
    match = re.search(r"/r/([A-Za-z0-9_-]+)", parsed.path)
    if match:
        form_id = match.group(1)
        print(f"Form ID:  {form_id}")
        print(f"\nNote: This is a short-link ID. You may need the full form GUID.")
        print(f"Open the form in edit mode and copy the 'id' from the URL instead.")
        print(f"\nUse it with:")
        print(f"  python scripts/manage_registry.py add-form --form-id \"{form_id}\" --form-name \"<name>\" --target-table \"<table>\"")
        return 0

    print("ERROR: Could not extract a form ID from this URL.")
    print()
    print("Expected URL formats:")
    print("  https://forms.office.com/Pages/DesignPageV2.aspx?id=<FORM_ID>&...")
    print("  https://forms.office.com/r/<FORM_ID>")
    print("  https://forms.microsoft.com/r/<FORM_ID>")
    print()
    print("Tip: Open the form in Microsoft Forms, click 'Share', and copy the link.")
    return 1


def cmd_diff(args: argparse.Namespace) -> int:
    print(f"Diff for form '{args.form_id}':")
    print()
    print("  This command will integrate with the schema monitor in a future release.")
    print("  For now, use git to compare changes:")
    print()
    print(f"    git diff config/form-registry.json")
    print(f"    git log --oneline -5 config/form-registry.json")
    return 0


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Manage the form-registry.json configuration file.",
    )
    parser.add_argument(
        "--registry",
        type=Path,
        default=DEFAULT_REGISTRY,
        help="Path to form-registry.json",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=DEFAULT_SCHEMA,
        help="Path to form-registry.schema.json",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # validate
    subparsers.add_parser("validate", help="Validate the registry file")

    # list
    subparsers.add_parser("list", help="List all registered forms")

    # add-form
    add_form = subparsers.add_parser(
        "add-form",
        help="Register a new form (paste the URL the clinician sent you)",
    )
    add_form.add_argument(
        "--form-url",
        help="Microsoft Forms URL — the form ID and name are extracted automatically",
    )
    add_form.add_argument(
        "--form-id",
        help="Form ID override (use instead of --form-url if you already have the GUID)",
    )
    add_form.add_argument(
        "--form-name",
        help="Display name override (auto-fetched from Forms API if omitted)",
    )
    add_form.add_argument("--target-table", required=True, help="Lakehouse table name (lowercase, underscores)")

    # add-field
    add_field = subparsers.add_parser("add-field", help="Add a field to an existing form")
    add_field.add_argument("--form-id", required=True, help="Form ID to add the field to (run 'lookup-id' to find it)")
    add_field.add_argument("--question-id", required=True, help="Question identifier")
    add_field.add_argument("--field-name", required=True, help="Column name")
    add_field.add_argument(
        "--contains-phi", action="store_true", default=False,
        help="Mark field as containing PHI",
    )
    add_field.add_argument(
        "--deid-method", default="none",
        choices=["hash", "redact", "generalize", "none"],
        help="De-identification method (default: none)",
    )
    add_field.add_argument(
        "--field-type", default=None,
        choices=["date", "age"],
        help="Semantic type hint (optional)",
    )

    # remove-form
    remove_form = subparsers.add_parser("remove-form", help="Remove a form entry")
    remove_form.add_argument("--form-id", required=True, help="Form to remove")
    remove_form.add_argument(
        "--yes", "-y", action="store_true", default=False,
        help="Skip confirmation prompt",
    )

    # diff
    diff_parser = subparsers.add_parser("diff", help="Show diff instructions (placeholder)")
    diff_parser.add_argument("--form-id", required=True, help="Form to diff")

    # lookup-id
    lookup_parser = subparsers.add_parser(
        "lookup-id",
        help="Extract a form ID from a Microsoft Forms URL",
    )
    lookup_parser.add_argument(
        "url",
        help="Microsoft Forms URL (e.g. https://forms.office.com/Pages/DesignPageV2.aspx?id=abc123...)",
    )

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    dispatch = {
        "validate": cmd_validate,
        "list": cmd_list,
        "add-form": cmd_add_form,
        "add-field": cmd_add_field,
        "remove-form": cmd_remove_form,
        "diff": cmd_diff,
        "lookup-id": cmd_lookup_id,
    }

    handler = dispatch.get(args.command)
    if handler is None:
        parser.print_help()
        return 1

    return handler(args)


if __name__ == "__main__":
    sys.exit(main())
