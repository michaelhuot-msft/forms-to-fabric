# Copilot Instructions

## Project: Forms to Fabric

This is a proof-of-concept reference implementation for a Microsoft Forms → Fabric data pipeline. Python Azure Functions, Bicep IaC, Power Automate flow templates.

## CI Requirements

All PRs must pass CI before merge. The CI pipeline validates:

1. **Python tests** — `python -m pytest tests/ -v` must pass with all tests green.
2. **Python linting** — `ruff check src/functions/ tests/` must pass with no errors.
3. **Python formatting** — `ruff format --check src/functions/ tests/` must pass.
4. **Bicep linting** — `az bicep build --file infra/main.bicep` must succeed with no errors.
5. **JSON schema validation** — `config/form-registry.json` must be valid against `config/form-registry.schema.json`.
6. **Credential scanning** — Automated secret/credential detection (gitleaks) must pass. No secrets, keys, or connection strings may be committed.

## Code Style

- Python 3.10+, type hints on all function signatures, docstrings on all public functions.
- Use `ruff` for linting and formatting (configured via pyproject.toml).
- Bicep files follow Azure naming conventions with `@description` decorators.
- Commit messages follow Conventional Commits format.

## Mermaid Diagrams

Do **not** use `<br>` or literal `\n` inside Mermaid node labels — they render inconsistently across GitHub, VS Code preview, and other Markdown renderers. Instead, use short single-line labels or split content across multiple connected nodes.

## Diagram Accessibility (WCAG 2.1 AA)

All diagrams (Mermaid and Excalidraw) must meet WCAG 2.1 AA standards:

- **Color contrast** — Text and meaningful graphical elements must have a contrast ratio of at least **4.5:1** against their background. Use dark stroke colors (`#1e1e1e`) on light fills. Avoid white text on medium-toned backgrounds.
- **Don't rely on color alone** — Convey meaning with labels, shapes, or patterns in addition to color.
- **Alt text** — When embedding diagram images (PNG/SVG exports), always include descriptive `alt` text.
- **Readable font sizes** — Use a minimum font size of 12px in Excalidraw diagrams.
- **Safe Mermaid style combos** — Use `fill:#dbeafe,color:#1e1e1e` (light fill, dark text), not `fill:#4472C4,color:#fff` (fails contrast).

## Architecture

- `src/functions/` — Python Azure Functions (v2 programming model)
- `infra/` — Bicep infrastructure-as-code
- `scripts/` — Admin CLI tools (manage_registry.py, rotate_function_key.py)
- `config/` — Form registry configuration + JSON schema
- `power-automate/` — Power Automate flow templates
- `docs/` — All documentation
- `tests/` — pytest test suite

## Infrastructure

- Fabric capacity provisioned via `infra/modules/fabric-capacity.bicep`
- Workspace and Lakehouse created via `scripts/Setup-FabricWorkspace.ps1` (Fabric REST API)
- All other Azure resources provisioned via Bicep modules in `infra/modules/`
- **Always run `az bicep build --file infra/main.bicep` after any Bicep changes** — do not commit if it fails
- A pre-commit hook validates Bicep automatically (install via `sh scripts/install-hooks.sh`)

## Key Patterns

- Form configs live in `config/form-registry.json` with schema validation
- De-identification uses hash/redact/generalize strategies per field
- Two-layer data model: raw (PHI, restricted) + curated (de-identified)
- Unregistered fields are quarantined (raw only, excluded from curated)
- Forms have status: active, pending_review, inactive
