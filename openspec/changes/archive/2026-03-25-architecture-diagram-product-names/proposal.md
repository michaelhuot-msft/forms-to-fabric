## Why

The architecture diagram in `docs/architecture.md` uses generic labels like "Registration form", "Registration flow", and "Blob registry" instead of the actual Microsoft product or service names. This makes it harder for readers to immediately understand which Microsoft technologies are involved and how they connect. Adding explicit product names (Microsoft Forms, Power Automate, Azure Functions, etc.) and visual grouping by platform improves clarity for stakeholders, IT reviewers, and new team members.

## What Changes

- Update the main architecture diagram in `docs/architecture.md` to use Microsoft product/service names in every node label
- Add platform-level subgraph groupings (Microsoft 365, Azure, Microsoft Fabric) so readers can visually distinguish which platform each component belongs to
- Use emoji or icon-style prefixes (e.g., 📋, ⚡, ⚙️) as additional visual signals alongside product names
- Ensure all existing connections and data flow relationships are preserved

## Capabilities

### New Capabilities
- `architecture-diagram-labels`: Update the Mermaid architecture diagram node labels to show Microsoft product/service names with visual platform groupings

### Modified Capabilities
<!-- No existing spec capabilities are being modified -->

## Impact

- **Docs**: `docs/architecture.md` — diagram section only, no prose changes
- **No code changes**: Documentation-only update
