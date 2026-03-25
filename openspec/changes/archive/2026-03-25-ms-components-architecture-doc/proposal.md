## Why

The project lacks a single visual document showing how all the Microsoft components (Forms, Power Automate, Azure Functions, Key Vault, Fabric/OneLake, Power BI, Entra ID) work together end-to-end. Stakeholders, new team members, and IT reviewers need a clear architectural reference that shows data flow, security boundaries, and component responsibilities — without having to read multiple code files and scripts.

## What Changes

- Add a new architecture document (`docs/architecture-overview.md`) with Mermaid diagrams illustrating:
  - End-to-end data flow from Microsoft Forms submission through to Power BI dashboards
  - Self-service form registration flow
  - Security and identity architecture (managed identity, Key Vault, Entra ID RBAC)
  - Two-layer data model (raw PHI vs curated de-identified) in Fabric Lakehouse
  - Component responsibilities and interactions
- Use the project's standard dual-mode Mermaid color palette for all diagrams
- Ensure all diagrams meet WCAG 2.1 AA accessibility requirements

## Capabilities

### New Capabilities
- `architecture-overview`: A comprehensive markdown document with Mermaid diagrams showing how all Microsoft components integrate, including data flow, security model, and the two-layer data architecture.

### Modified Capabilities
<!-- No existing capabilities are being modified — this is a new documentation artifact. -->

## Impact

- **Docs**: New file `docs/architecture-overview.md`
- **No code changes**: This is documentation only — no changes to source code, infrastructure, or tests
- **README**: May add a link to the new architecture doc from the main README
