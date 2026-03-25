## 1. Document Setup

- [x] 1.1 Create `docs/architecture-overview.md` with title, table of contents, and introductory paragraph
- [x] 1.2 Add the standard dual-mode Mermaid classDef palette block (primary, success, warning, danger, info, neutral)

## 2. Component Reference Table

- [x] 2.1 Add a component responsibility table listing all 12 Microsoft components (Forms, Power Automate, Azure Functions, Key Vault, Storage, App Insights, Fabric Capacity, Fabric Lakehouse, OneLake, Power BI, Entra ID, Graph API) with role and key details

## 3. End-to-End Data Flow Diagram

- [x] 3.1 Create a Mermaid flowchart (TD) showing the complete data path: Forms → Power Automate → Azure Functions `/api/process-response` → OneLake raw layer → de-identification → OneLake curated layer → Power BI
- [x] 3.2 Include Key Vault authentication on the Power Automate → Functions connection
- [x] 3.3 Add annotations showing where de-identification occurs and the error/alert path via Outlook

## 4. Self-Service Registration Flow Diagram

- [x] 4.1 Create a Mermaid flowchart (LR) showing: registration intake form → Power Automate → `/api/register-form` → form-registry update → per-form flow creation
- [x] 4.2 Include the conditional PHI review gate: `pending_review` status → IT activation via `/api/activate-form` → `active` status

## 5. Security & Identity Diagram

- [x] 5.1 Create a Mermaid diagram showing the security architecture: managed identity from Azure Functions to Key Vault, Storage, and Fabric/OneLake
- [x] 5.2 Label each connection with its authentication method (managed identity, function key, bearer token, Entra ID)
- [x] 5.3 Show Entra ID RBAC for Fabric workspace access (Admin → raw layer, Analyst → curated layer)

## 6. Two-Layer Data Model

- [x] 6.1 Create a Mermaid diagram showing raw and curated layers as distinct elements with access controls
- [x] 6.2 Add a de-identification methods table (hash, redact, generalize, encrypt, none) with descriptions and examples
- [x] 6.3 Include the de-identification decision tree as a flowchart or descriptive section

## 7. Integration & Finalize

- [x] 7.1 Add a link to `docs/architecture-overview.md` from the project README.md documentation section
- [x] 7.2 Verify all Mermaid diagrams use only the standard classDef palette and have no color-only meaning
- [x] 7.3 Verify the document renders correctly with all diagrams visible
