# Copilot Instructions

## Project: Forms to Fabric

This is a proof-of-concept reference implementation for a Microsoft Forms → Fabric data pipeline. Python Azure Functions, Bicep IaC, Power Automate flow templates.

## CI Requirements

All PRs must pass CI before merge. The CI pipeline validates:

1. **Python tests** — `python -m pytest tests/ -v` must pass with all tests green.
2. **Python linting** — `ruff check src/functions/ tests/` must pass with no errors.
3. **Python formatting** — `ruff format --check src/functions/ tests/` must pass.
4. **Bicep linting** — `az bicep build --file infra/main.bicep` must succeed with no errors.
5. **Credential scanning** — Automated secret/credential detection (gitleaks) must pass. No secrets, keys, or connection strings may be committed.

## Code Style

- Python 3.11+, type hints on all function signatures, docstrings on all public functions.
- Use `ruff` for linting and formatting (configured via pyproject.toml).
- Bicep files follow Azure naming conventions with `@description` decorators.
- Commit messages follow Conventional Commits format.

## Mermaid Diagrams

- Use Mermaid syntax for architecture and flow diagrams in markdown.
- Do NOT use `<br>` or literal `\n` inside Mermaid node labels.

### Standard Dual-Mode Palette

Use this palette for all Mermaid diagrams. Every color is WCAG AA compliant (≥4.5:1 text contrast) and visible on both light and dark backgrounds.

| Role | Fill | Stroke | Text | Use For |
|---|---|---|---|---|
| **Primary** | `#4dabf7` | `#1864ab` | `#1a1a2e` | Main flow, default nodes |
| **Success** | `#69db7c` | `#2b8a3e` | `#1a1a2e` | Completed, healthy, valid |
| **Warning** | `#ffd43b` | `#e67700` | `#1a1a2e` | Caution, pending review |
| **Danger** | `#ff8787` | `#c92a2a` | `#1a1a2e` | Errors, critical, blocked |
| **Info** | `#b197fc` | `#6741d9` | `#1a1a2e` | Metadata, supporting info |
| **Neutral** | `#ced4da` | `#495057` | `#1a1a2e` | Background, inactive, optional |

Copy this `classDef` block into Mermaid diagrams:

```
classDef primary fill:#4dabf7,stroke:#1864ab,color:#1a1a2e
classDef success fill:#69db7c,stroke:#2b8a3e,color:#1a1a2e
classDef warning fill:#ffd43b,stroke:#e67700,color:#1a1a2e
classDef danger fill:#ff8787,stroke:#c92a2a,color:#1a1a2e
classDef info fill:#b197fc,stroke:#6741d9,color:#1a1a2e
classDef neutral fill:#ced4da,stroke:#495057,color:#1a1a2e
```

Do **not** use: `fill:#dbeafe` (invisible on dark), `fill:#d3f9d8` (invisible on dark), `fill:#1e1e1e` (invisible on dark), or any pastel fills without strokes.

### Accessibility (WCAG 2.1 AA)

All diagrams must meet WCAG 2.1 AA:
- **Color contrast** ≥ 4.5:1 for text on backgrounds
- **No color-only meaning** — use labels, shapes, or patterns
- **Alt text** for embedded images
- **Font size** ≥ 12px in Excalidraw

## Architecture

- `src/functions/` — Python Azure Functions (v2 programming model)
- `infra/` — Bicep infrastructure-as-code
- `scripts/` — Admin CLI tools (Manage-Registry.ps1, rotate_function_key.py)
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
