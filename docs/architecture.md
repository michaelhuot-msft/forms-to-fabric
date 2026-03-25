# Forms to Fabric — Architecture

> **Audience:** IT Leadership, Security, and Compliance Teams
> **Last Updated:** 2026-03-08


---

## System Overview

The Forms to Fabric pipeline enables clinicians to submit structured data through Microsoft Forms, which is automatically processed, de-identified, and delivered to a Microsoft Fabric Lakehouse for analytics and reporting. The pipeline is fully contained within the Microsoft cloud ecosystem, requires no third-party services, and enforces a two-layer data model that separates protected health information (PHI) from reporting-ready data. It also includes a self-service registration flow that creates per-form Power Automate pipelines and failure-alert emails for operators.

All infrastructure is defined as code using Bicep and deployed via the Azure Developer CLI (`azd`). Secrets are managed through Azure Key Vault, and observability is provided by Application Insights.

### Architecture Diagram

```mermaid
flowchart TB
    subgraph M365["Microsoft 365"]
        RegForm["📋 Microsoft Forms (Registration intake)"]
        Survey["📋 Microsoft Forms (Data collection)"]
        RegFlow["⚡ Power Automate (Registration flow)"]
        PerFlow["⚡ Power Automate (Per-form data flows)"]
        Alerts["✉️ Outlook (Failure alert email)"]
    end

    subgraph Azure["Azure Platform"]
        Register["⚙️ Azure Functions (/api/register-form)"]
        Activate["⚙️ Azure Functions (/api/activate-form)"]
        Process["⚙️ Azure Functions (/api/process-response)"]
        FlowApi["⚙️ Power Platform API (Flow creation)"]
        Registry["🗄️ Azure Blob Storage (Form registry)"]
    end

    subgraph Fabric["Microsoft Fabric"]
        Lakehouse["📊 Fabric Lakehouse (Raw + Curated)"]
        PowerBI["📊 Power BI (DirectLake dashboards)"]
    end

    RegForm --> RegFlow --> Register
    Register --> Registry
    Register --> FlowApi --> PerFlow
    Activate --> Registry
    Survey --> PerFlow --> Process
    Process --> Registry
    Process --> Lakehouse --> PowerBI
    PerFlow --> Alerts

    classDef primary fill:#4dabf7,stroke:#1864ab,color:#1a1a2e
    classDef success fill:#69db7c,stroke:#2b8a3e,color:#1a1a2e
    classDef warning fill:#ffd43b,stroke:#e67700,color:#1a1a2e
    classDef danger fill:#ff8787,stroke:#c92a2a,color:#1a1a2e
    classDef info fill:#b197fc,stroke:#6741d9,color:#1a1a2e
    classDef neutral fill:#ced4da,stroke:#495057,color:#1a1a2e

    class RegForm,Survey primary
    class RegFlow,PerFlow,Alerts warning
    class Register,Activate,Process,FlowApi,Registry info
    class Lakehouse,PowerBI success
```

---

## Component Descriptions

| Component | Role | Key Details |
|---|---|---|
| **Microsoft Forms** | Data capture | Clinicians create and submit structured forms. Responses are transient; no PHI is stored long-term in Forms. Lives within the M365 tenant. |
| **Power Automate** | Event-driven orchestration | The registration flow provisions per-form data flows, and each per-form flow retrieves Forms responses, posts them to the Azure Function, and sends failure email alerts when processing fails. |
| **Azure Function (Python)** | Core processing engine | Validates the incoming payload, looks up per-form configuration in `form-registry.json`, applies de-identification rules, and writes to both raw and curated Lakehouse layers. Runs on a Consumption plan. Authenticates to downstream services via managed identity. |
| **Azure Key Vault** | Secrets management | Stores function keys, connection strings, and encryption keys. Accessed exclusively via managed identity — no credentials in code or configuration files. Soft-delete and purge protection enabled. |
| **Application Insights** | Monitoring and diagnostics | Tracks function execution performance, error rates, and custom metrics (e.g., records processed, de-identification operations). Powers operational alerting and dashboards. |
| **Storage Account** | Function infrastructure | Provides the backing store required by the Azure Functions runtime. Also used for deployment artifacts managed by `azd`. |
| **Fabric Capacity** | Infrastructure | Fabric compute capacity (F2+ SKU) provisioned via Bicep (`infra/modules/fabric-capacity.bicep`). Assigned to the workspace that hosts the Lakehouse. Scales from F2 (dev) to F64 (production). |
| **Microsoft Fabric Lakehouse** | Analytical data store | Two-layer architecture (raw + curated) built on OneLake. Data stored in Delta Lake format for ACID transactions, time travel, and schema enforcement. |
| **Power BI** | Reporting and visualization | Connects to the Lakehouse in DirectLake mode for near-real-time queries without data duplication. Supports row-level security for department-scoped access. |
| **Schema Monitor** (`monitor_schema`) | Automated compliance | Timer-triggered function (every 6 hours) that compares registered schemas and logs detected changes. The current implementation logs alerts and can be extended to send notifications. |
| **RBAC Auditor** (`audit_rbac`) | Access compliance | Daily timer-triggered function that audits Fabric workspace role assignments. Flags any non-admin user with access to raw (PHI) layer and logs violations to Application Insights. |
| **Flow Generator** (`generate_flow`) | Admin automation | HTTP endpoint that generates workflow-definition JSON for manual troubleshooting or custom automation. The normal registration path uses `flow_create_body` returned by `register_form`. |
| **Registration Endpoint** (`register_form`) | Self-service onboarding | HTTP POST endpoint (`/api/register-form`) that accepts a form URL, short name, and PHI flag. Creates a form-registry entry and returns `flow_create_body` plus a status of `active` or `pending_review`. |
| **Activation Endpoint** (`activate_form`) | Admin approval | HTTP POST endpoint (`/api/activate-form`) that transitions a form from `pending_review` to `active` after IT classifies PHI fields. |

---

## Administrative Automation

Three automated functions run alongside the core processing pipeline to reduce manual administration:

- **Schema Monitor** detects form structure changes every 6 hours and logs the deltas for review.
- **RBAC Auditor** checks Fabric workspace access daily at 8 AM UTC and flags unauthorized raw-layer access.
- **Flow Generator** provides on-demand workflow-definition JSON for debugging or advanced/manual flow automation.
- **Self-Service Registration** allows clinicians to register forms via a simple 3-question Microsoft Form. The registration flow calls `register-form`, stores the returned status, and posts `flow_create_body` to the Flow API to create the per-form flow. PHI forms remain `pending_review` until IT activates them.
- **Fabric Capacity Workflow** suspends the capacity nightly and allows manual or deploy-time resume.
- **Registry Management CLI** (`scripts/Manage-Registry.ps1`) lists and manages `form-registry.json` entries.
- **Key Rotation Script** (`scripts/rotate_function_key.py`) automates function key rotation with zero-downtime.

```mermaid
flowchart LR
    SM["Schema Monitor every 6 hours"] --> AI["Application Insights"]
    RA["RBAC Auditor daily"] --> FABRIC["Fabric Workspace"]
    FG["Flow Generator on demand"] --> DEF["Workflow definition JSON"]
    CAP["GitHub Actions capacity workflow"] --> FABRIC

    classDef primary fill:#4dabf7,stroke:#1864ab,color:#1a1a2e
    classDef info fill:#b197fc,stroke:#6741d9,color:#1a1a2e
    classDef success fill:#69db7c,stroke:#2b8a3e,color:#1a1a2e

    class SM,RA,FG,CAP primary
    class AI,FABRIC,DEF info
```

---

## Data Flow

The following sequence describes the end-to-end processing of a single form submission:

1. **Clinician submits** a response via Microsoft Forms.
2. **Power Automate trigger fires** automatically on the new submission event.
3. **Power Automate retrieves** the full response details from the Forms service.
4. **Power Automate sends an HTTP POST** to the Azure Function endpoint with the current raw-response payload:
   - `form_id`
   - `raw_response` (the full Forms response body)
5. **Azure Function validates** the request and looks up the form configuration in `form-registry.json` to determine field-level processing rules.
6. **Function writes the raw response** to the Lakehouse **raw layer** — all fields, unmodified — for audit and reprocessing purposes.
7. **Function applies de-identification rules** per the field configuration (redact, hash, generalize, encrypt, or pass-through).
8. **Function writes the de-identified response** to the Lakehouse **curated layer** for downstream analytics.
9. **Function returns HTTP 200 OK** to Power Automate (or an appropriate error code with diagnostic details).
10. **Power BI dashboards reflect new data** via DirectLake mode with near-real-time latency.

```mermaid
sequenceDiagram
    participant C as Clinician
    participant MF as Microsoft Forms
    participant PA as Power Automate
    participant AF as Azure Function
    participant FR as Form Registry
    participant Raw as OneLake Raw
    participant Cur as OneLake Curated
    participant PBI as Power BI

    C->>MF: 1. Submit response
    MF->>PA: 2. Trigger fires on new submission
    PA->>MF: 3. Retrieve full response details
    PA->>AF: 4. HTTP POST (form_id, raw_response)
    AF->>FR: 5. Look up form config & field rules
    AF->>Raw: 6. Write raw response (all fields, unmodified)
    Note over AF: 7. Apply de-identification rules (redact, hash, generalize, encrypt, none)
    AF->>Cur: 8. Write de-identified response
    AF->>PA: 9. Return HTTP 200 OK
    PBI->>Cur: 10. DirectLake query reflects new data
```

---

## Security Controls

### Authentication & Authorization

- **Azure Function** uses a system-assigned **managed identity** — no stored credentials in code, configuration, or environment variables.
- **Power Automate** authenticates to the Azure Function via a **function key** stored securely in Key Vault.
- **Fabric workspace access** is controlled via Azure AD **role-based access control (RBAC)**.
- **Power BI row-level security** is available for department-level data isolation within shared reports.

### Data Protection

| Control | Implementation |
|---|---|
| Data in transit | HTTPS / TLS 1.2+ enforced on all endpoints |
| Data at rest | Encrypted with Azure-managed keys (option for customer-managed keys via Key Vault) |
| Key Vault protection | RBAC access model, soft-delete enabled, purge protection enabled |
| Tenant boundary | No data leaves the Microsoft tenant boundary at any stage of processing |

### Network Security

- All communication occurs over the **Microsoft backbone network**.
- Azure Function can be configured with **VNet integration** for additional network isolation (optional enhancement).
- Fabric Lakehouse is accessed via **Microsoft internal endpoints** (OneLake API).
- **No public internet egress** for data at any point in the pipeline.

---

## PHI Handling

### Two-Layer Data Model

| Layer | Classification | Contents | Access | Purpose |
|---|---|---|---|---|
| **Raw** | Restricted | Original, unmodified response data including PHI | IT Administrators and authorized data engineers only | Audit trail, re-processing, compliance investigations |
| **Curated** | Shared | De-identified data with PHI removed or transformed | Department leads, analysts, clinicians | Dashboards, reporting, operational analytics |

### De-Identification Methods

The Azure Function applies one of the following de-identification methods to each field based on the form's configuration in `form-registry.json`:

| Method | Description | Use Case | Example |
|---|---|---|---|
| **Redact** | Replace value with a placeholder string | Names, email addresses, free-text identifiers | `"John Smith"` → `"[REDACTED]"` |
| **Hash** | Apply SHA-256 one-way hash | MRN, patient IDs, record identifiers | `"MRN-12345"` → `"a3f2b8..."` |
| **Generalize** | Reduce precision to prevent re-identification | Date of birth, postal codes | `"1985-03-15"` → `"1985"` |
| **Encrypt** | Reversible encryption using a Key Vault–managed key | Fields that may require authorized re-identification | Original value → encrypted blob |
| **None** | Pass through unchanged | Non-identifying data: ratings, yes/no, counts | `"4"` → `"4"` |

#### De-Identification Decision Tree

```mermaid
flowchart TD
    A{"Is this field PHI or PII?"} -->|No| B["non_sensitive / none"]
    A -->|Yes| C{"Does it directly identify a person?"}
    C -->|Yes| D["direct_identifier"]
    C -->|No| E["quasi_identifier"]
    D --> F{"Need to link records?"}
    F -->|Yes| G["hash"]
    F -->|No| H{"Need original value later?"}
    H -->|Yes| I["encrypt"]
    H -->|No| J["redact"]
    E --> K{"Aggregate analysis needed?"}
    K -->|Yes| L["generalize"]
    K -->|No| M["redact"]
```

### Access Controls

- **Raw layer:** Restricted to IT Admin role (Fabric workspace Admin).
- **Curated layer:** Department-scoped access via Fabric workspace roles.
- **Power BI:** Row-level security enforced by department affiliation.
- **Audit trail:** All data access is logged and available for compliance review.

#### Access Control Model

```mermaid
flowchart LR
    subgraph RawAccess["Raw Layer (Restricted)"]
        raw_layer["Raw Data - Full PHI"]
    end

    subgraph CuratedAccess["Curated Layer (Shared)"]
        curated_layer["De-identified Data - PHI Removed"]
    end

    subgraph PBIAccess["Power BI (Row-Level Security)"]
        pbi_rls["Department-Scoped Reports"]
    end

    admin["IT Admins"] --> raw_layer
    leads["Department Leads"] --> curated_layer
    analysts["Analysts"] --> curated_layer
    clinicians["Clinicians"] --> pbi_rls
    curated_layer --> pbi_rls
```

---

## Compliance Considerations

### HIPAA

| Requirement | How It Is Addressed |
|---|---|
| **Business Associate Agreement (BAA)** | Required with Microsoft; covers M365, Azure, and Fabric services. |
| **Minimum Necessary Principle** | The curated layer exposes only de-identified data. Raw layer access is restricted to authorized personnel with a documented need. |
| **Audit Logging** | All access is tracked via Azure Monitor, Application Insights, and Fabric audit logs. |
| **Breach Notification** | Application Insights alerts configured for unauthorized access patterns, function failures, and anomalous activity. |

### Data Residency

- All Azure resources are deployed in a **single Azure region** (configurable; default: **Canada East**).
- Data **does not leave the Microsoft cloud boundary** at any stage.
- **No third-party services** are involved in the pipeline.
- Fabric capacity is provisioned in the **same region** as Azure resources to maintain data locality.

### Audit Logging

All components produce audit-grade logs that can be aggregated for compliance reporting:

| Source | Retention (Default) | Contents |
|---|---|---|
| Azure Function execution logs | 90 days (Application Insights) | Request/response metadata, processing outcomes, errors |
| Power Automate flow run history | 28 days | Trigger events, HTTP call results, failure details |
| Key Vault access logs | Continuous (Azure Monitor) | Secret reads, key operations, access denials |
| Fabric workspace audit logs | 30 days (extendable) | Data access, query execution, permission changes |

All logs can be exported to a centralized **SIEM** solution for long-term retention and correlation.

---

## Disaster Recovery and Data Retention

### Recovery

| Aspect | Approach |
|---|---|
| **Infrastructure** | Fully redeployable via `azd up` — all resources defined as Bicep templates in source control. |
| **Application Code** | Version-controlled in Git with CI/CD pipeline support. |
| **Data** | OneLake provides built-in redundancy; Delta Lake format supports time travel for point-in-time recovery. |
| **RPO** | 1 hour — data in transit at the time of failure may require resubmission. |
| **RTO** | 4 hours — redeploy infrastructure, restore configuration, and reconnect Power Automate flows. |

### Data Retention

| Data Store | Default Retention | Notes |
|---|---|---|
| Lakehouse — Raw layer | 7 years | Per organizational healthcare data retention policy |
| Lakehouse — Curated layer | Per organizational policy | Aligned with reporting and compliance requirements |
| Application Insights | 90 days | Configurable up to 730 days |
| Power Automate run history | 28 days | Microsoft platform default |
| Key Vault soft-delete | 90 days | Protects against accidental secret deletion |

---

## Network Architecture

All components operate within the Microsoft cloud ecosystem. No data traverses the public internet.

| Path | Transport | Notes |
|---|---|---|
| Microsoft Forms → Power Automate | Internal M365 service-to-service | Automatic trigger via Microsoft Graph |
| Power Automate → Azure Function | HTTPS over Microsoft backbone | Authenticated via function key from Key Vault |
| Azure Function → Key Vault | Azure internal network | Authenticated via managed identity |
| Azure Function → Fabric Lakehouse | HTTPS via OneLake API over Microsoft backbone | Authenticated via managed identity or service principal |
| Fabric Lakehouse → Power BI | Internal Fabric service-to-service | DirectLake mode — no data copy required |

**Key guarantees:**

- No data traverses the public internet.
- No third-party services or external APIs are invoked.
- **Optional enhancement:** VNet integration for the Azure Function provides an additional layer of network isolation, restricting outbound traffic to approved endpoints only.

---

---

## Known Limitations and Recommendations

### Re-registration does not update existing entries

If a clinician re-registers a form that is already in the pipeline, the system returns a success confirmation but does **not** update the existing registry entry. This means:

- **Changed PHI status** — If a clinician initially registered as "No patient info" but later added PHI fields and re-registers with "Yes", the registry is not updated. The schema monitor will detect the new fields and IT can classify them manually.
- **Recommendation for future:** Add an "update" path where re-registration with a different PHI flag updates the existing entry and triggers an IT review notification.

### New form fields are captured but not classified

When a clinician adds new questions to an already-registered form:

- **Raw layer** — New fields are captured automatically via the `raw_response` passthrough (no data loss)
- **Curated layer** — New fields are excluded until IT classifies them with de-identification methods
- **Schema monitor** — Detects changes every 6 hours and alerts IT
- **Recommendation:** This is the intended "safe by default" behavior. No code changes needed.

### Data pipeline flow uses the registering user's connections

When the Azure Function auto-creates a data pipeline flow via the Flow Management API:

- The flow is created under the Function App's identity
- The Forms trigger connector may require the form owner to authorize the connection
- **Recommendation:** Verify that auto-created flows have valid connections. If the Forms connector needs user authorization, the clinician may need to open the flow once and authorize.

---

*This document should be reviewed and updated whenever the pipeline architecture changes or new compliance requirements are introduced.*
