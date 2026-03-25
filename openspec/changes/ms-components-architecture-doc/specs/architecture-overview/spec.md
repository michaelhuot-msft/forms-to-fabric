## ADDED Requirements

### Requirement: Architecture overview document exists
The project SHALL have a `docs/architecture-overview.md` file that provides a comprehensive visual reference of how all Microsoft components integrate.

#### Scenario: Document is accessible from README
- **WHEN** a user reads the project README
- **THEN** there SHALL be a link to `docs/architecture-overview.md` in the documentation section

#### Scenario: Document renders on GitHub
- **WHEN** a user views `docs/architecture-overview.md` on GitHub
- **THEN** all Mermaid diagrams SHALL render correctly as visual diagrams

### Requirement: End-to-end data flow diagram
The document SHALL include a Mermaid flowchart showing the complete data path from Microsoft Forms submission through Power Automate, Azure Functions processing, and into Fabric Lakehouse, ending at Power BI dashboards.

#### Scenario: All processing components shown
- **WHEN** a reader views the end-to-end data flow diagram
- **THEN** the diagram SHALL show: Microsoft Forms, Power Automate, Azure Functions (`/api/process-response`), Azure Key Vault, OneLake (raw layer), OneLake (curated layer), and Power BI

#### Scenario: Data transformation visible
- **WHEN** a reader views the data flow diagram
- **THEN** the diagram SHALL clearly indicate where de-identification occurs (between raw write and curated write in Azure Functions)

### Requirement: Self-service registration flow diagram
The document SHALL include a Mermaid diagram showing the form registration pipeline: intake form submission → `/api/register-form` → per-form Power Automate flow creation.

#### Scenario: Registration steps shown
- **WHEN** a reader views the registration flow diagram
- **THEN** the diagram SHALL show: registration intake form, Power Automate registration flow, Azure Functions `/api/register-form` endpoint, form registry update, and per-form flow creation

#### Scenario: PHI review gate visible
- **WHEN** a reader views the registration flow diagram
- **THEN** the diagram SHALL show the conditional path where forms with PHI enter `pending_review` status and require IT activation via `/api/activate-form`

### Requirement: Security and identity diagram
The document SHALL include a Mermaid diagram showing the security architecture: managed identity flows, Key Vault integration, Entra ID RBAC, and authentication methods between components.

#### Scenario: Managed identity shown
- **WHEN** a reader views the security diagram
- **THEN** the diagram SHALL show Azure Functions using system-assigned managed identity to access Key Vault, Storage, and Fabric/OneLake

#### Scenario: Authentication methods labeled
- **WHEN** a reader views the security diagram
- **THEN** each connection between components SHALL be labeled with its authentication method (managed identity, function key, bearer token, Entra ID)

### Requirement: Two-layer data model diagram
The document SHALL include a visual representation of the raw (PHI) and curated (de-identified) data layers in Fabric Lakehouse, including de-identification methods.

#### Scenario: Both layers shown with access controls
- **WHEN** a reader views the data model diagram
- **THEN** the diagram SHALL show the raw layer (restricted to IT Admins) and curated layer (accessible to analysts via Power BI) as distinct visual elements

#### Scenario: De-identification methods listed
- **WHEN** a reader views the data model section
- **THEN** the document SHALL list all de-identification methods (hash, redact, generalize, encrypt, none) with brief descriptions

### Requirement: WCAG AA compliant diagrams
All Mermaid diagrams SHALL use the project's standard dual-mode color palette and meet WCAG 2.1 AA accessibility requirements.

#### Scenario: Standard palette used
- **WHEN** a diagram uses color to distinguish components
- **THEN** it SHALL use only the classDef colors defined in the project's standard palette (primary, success, warning, danger, info, neutral)

#### Scenario: No color-only meaning
- **WHEN** a diagram conveys meaning through color
- **THEN** it SHALL also use text labels or distinct shapes so the meaning is accessible without color perception

### Requirement: Component responsibility table
The document SHALL include a table listing each Microsoft component, its role in the architecture, and key details.

#### Scenario: All components listed
- **WHEN** a reader views the component table
- **THEN** it SHALL include: Microsoft Forms, Power Automate, Azure Functions, Azure Key Vault, Azure Storage, Application Insights, Fabric Capacity, Fabric Lakehouse, OneLake, Power BI, Entra ID, and Microsoft Graph API
