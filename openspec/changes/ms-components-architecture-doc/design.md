## Context

The Forms-to-Fabric project has extensive documentation spread across README, setup guides, and inline code comments, but no single visual architecture reference. Stakeholders (clinicians, IT admins, new developers) need to quickly understand how Microsoft Forms submissions flow through Power Automate, Azure Functions, and into Fabric Lakehouse — including security boundaries and the two-layer data model.

The project uses 11+ Microsoft components that integrate via REST APIs, managed identity, and M365 connectors. The current docs explain individual setup steps but don't show the holistic picture.

## Goals / Non-Goals

**Goals:**
- Create a single `docs/architecture-overview.md` that serves as the canonical architecture reference
- Include Mermaid diagrams for: end-to-end data flow, registration flow, security model, and two-layer data architecture
- Use the project's standard dual-mode Mermaid color palette (WCAG AA compliant)
- Make the document useful for onboarding, IT review, and stakeholder presentations

**Non-Goals:**
- Replacing existing setup guides or runbooks
- Documenting deployment steps or CLI commands (those live in setup-guide.md)
- Creating interactive diagrams or external tooling (Mermaid in markdown only)
- Covering future/planned features — document current state only

## Decisions

### 1. Single document vs multiple pages
**Decision**: Single `docs/architecture-overview.md` with internal anchors.
**Rationale**: A single file is easier to maintain, link to, and render on GitHub. The content fits comfortably in one document with sections. Multiple pages would fragment the narrative and require cross-linking.

### 2. Mermaid diagram types
**Decision**: Use `flowchart TD` for data flows, `flowchart LR` for the registration flow, `block-beta` or `flowchart` for the security model, and a table + flowchart for the two-layer data model.
**Rationale**: Flowcharts best represent the sequential data pipeline. Left-to-right orientation suits the registration flow's linear nature. Tables complement diagrams for the data model details.
**Alternative considered**: Sequence diagrams — rejected because they emphasize timing over component relationships, and the audience cares more about "what connects to what" than message ordering.

### 3. Color palette
**Decision**: Use the project's existing dual-mode classDef palette from CONTRIBUTING.md / copilot instructions.
**Rationale**: Consistency with existing project diagrams. Already verified WCAG AA compliant on both light and dark backgrounds.

### 4. Diagram scope
**Decision**: Four diagrams covering distinct concerns:
  1. **End-to-end data flow** — Forms → Power Automate → Azure Functions → OneLake → Power BI
  2. **Self-service registration flow** — intake form → register-form API → per-form flow creation
  3. **Security & identity architecture** — managed identity, Key Vault, Entra ID roles
  4. **Two-layer data model** — raw (PHI) vs curated (de-identified) with de-identification methods
**Rationale**: Four focused diagrams are clearer than one overloaded diagram. Each addresses a distinct stakeholder question.

## Risks / Trade-offs

- **[Risk] Diagrams become stale as architecture evolves** → Mitigation: Keep diagrams high-level (component names, not implementation details). Add a "Last updated" note. Reference from README so it stays visible.
- **[Risk] Mermaid rendering varies across GitHub/VS Code/other viewers** → Mitigation: Test rendering on GitHub. Stick to well-supported Mermaid features (flowchart, classDef). Avoid experimental syntax.
- **[Risk] Document becomes too long for quick reference** → Mitigation: Use a table of contents with anchor links. Keep each section self-contained so readers can jump to what they need.
