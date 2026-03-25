## Context

The `docs/architecture.md` diagram currently uses generic descriptive labels (e.g., "Registration form", "Per-form data flows", "Blob registry"). Readers must mentally map these to the actual Microsoft products. The diagram also lacks visual grouping by platform.

## Goals / Non-Goals

**Goals:**
- Replace all generic node labels with Microsoft product/service names
- Add platform subgraph groupings (M365, Azure, Fabric) for visual clarity
- Add emoji prefixes as supplementary visual signals (not color-only meaning)
- Preserve all existing connections and flow relationships

**Non-Goals:**
- Changing the diagram layout (TB orientation) or adding new nodes
- Modifying any prose content in architecture.md
- Updating other diagrams in the document (sequence diagram, admin automation, access control, de-id tree)

## Decisions

### 1. Node label format
**Decision**: `"emoji Product Name (role)"` — e.g., `"📋 Microsoft Forms (Registration intake)"`
**Rationale**: The emoji provides a quick visual scan signal. The product name gives the canonical Microsoft name. The parenthetical role clarifies the specific function in this pipeline.
**Alternative considered**: Product name only without role — rejected because some products appear multiple times (e.g., Forms for registration vs data collection).

### 2. Platform subgraph groupings
**Decision**: Three subgraphs: `Microsoft 365`, `Azure Platform`, `Microsoft Fabric`
**Rationale**: Maps to the three distinct Microsoft platforms used. Helps readers understand licensing and administration boundaries.
**Alternative considered**: Two groups (M365 vs Azure+Fabric) — rejected because Fabric has distinct identity and is increasingly its own platform.

### 3. Emoji selection
**Decision**: Use unicode emoji that render reliably in GitHub Mermaid: 📋 (forms/data), ⚡ (automation), ⚙️ (processing), 🔑 (secrets), 📊 (analytics), ✉️ (email), 🗄️ (storage)
**Rationale**: These render across GitHub, VS Code, and most markdown renderers. They add a second visual channel beyond color.

## Risks / Trade-offs

- **[Risk] Emoji rendering inconsistency across platforms** → Mitigation: Emoji are supplementary — product names and labels carry the full meaning. Diagram remains readable without emoji.
- **[Risk] Longer labels make diagram wider** → Mitigation: Use concise role descriptions in parentheses. The TB layout handles wider nodes well.
