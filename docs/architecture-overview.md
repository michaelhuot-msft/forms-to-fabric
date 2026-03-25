# Forms to Fabric — Architecture Overview

> **Audience:** IT Leadership, Developers, New Team Members
> **Purpose:** Visual architecture reference showing how all Microsoft components integrate
> **See also:** [Architecture (detailed)](architecture.md) for compliance, DR, and network details

---

## Contents

- [Component Map](#component-map)
- [End-to-End Data Flow](#end-to-end-data-flow)
- [Self-Service Registration Flow](#self-service-registration-flow)
- [Security and Identity](#security-and-identity)
- [Two-Layer Data Model](#two-layer-data-model)

<!--
  Standard dual-mode Mermaid palette (WCAG AA compliant on light and dark backgrounds).
  Copy the classDef block below into each diagram.

  classDef primary fill:#4dabf7,stroke:#1864ab,color:#1a1a2e
  classDef success fill:#69db7c,stroke:#2b8a3e,color:#1a1a2e
  classDef warning fill:#ffd43b,stroke:#e67700,color:#1a1a2e
  classDef danger fill:#ff8787,stroke:#c92a2a,color:#1a1a2e
  classDef info fill:#b197fc,stroke:#6741d9,color:#1a1a2e
  classDef neutral fill:#ced4da,stroke:#495057,color:#1a1a2e
-->

---

## Component Map

| Component | Type | Role |
|---|---|---|
| **Microsoft Forms** | M365 — Data Capture | Clinicians create and submit structured questionnaires. Responses are transient — no long-term PHI in Forms. |
| **Power Automate** | M365 — Orchestration | Triggers on form submission, retrieves response details, POSTs to Azure Function, sends failure alerts via Outlook. |
| **Azure Functions** (Python 3.11) | Azure — Processing | Validates payloads, looks up form config, writes raw data, applies de-identification, writes curated data. 6 HTTP + 3 timer endpoints. |
| **Azure Key Vault** | Azure — Secrets | Stores function keys and encryption keys. Accessed only via managed identity. Soft-delete + purge protection enabled. |
| **Azure Storage** | Azure — Infrastructure | Backing store for Functions runtime. Hosts `form-registry.json` blob in `form-registry` container. |
| **Application Insights** | Azure — Monitoring | Tracks function performance, error rates, custom metrics (records processed, de-id operations, schema changes). |
| **Fabric Capacity** | Fabric — Compute | Allocates compute for analytics. Provisioned via Bicep (F2 dev to F64 prod). Suspendable nightly via GitHub Actions. |
| **Fabric Lakehouse** | Fabric — Storage | Two-layer architecture: raw (PHI, restricted) + curated (de-identified, shared). Delta Lake format with ACID and time travel. |
| **OneLake** | Fabric — File Store | Cloud storage backend using Parquet/Delta. URI: `abfss://{workspace}@onelake.dfs.fabric.microsoft.com/{lakehouse}/Tables/...` |
| **Power BI** | Fabric — Reporting | DirectLake mode for near-real-time queries on curated data. Row-level security for department-scoped access. |
| **Microsoft Entra ID** | Identity — RBAC | Manages workspace roles (Admin for raw layer, Contributor/Viewer for curated). Groups-based access control. |
| **Microsoft Graph API** | M365 — Metadata | Used by schema monitor to retrieve live form structure and detect question changes. |

---

## End-to-End Data Flow

This diagram shows the complete path of a single form submission — from clinician input through to Power BI dashboards.

```mermaid
flowchart TD
    Forms["Microsoft Forms\n(Clinician submits response)"]
    PA["Power Automate\n(Trigger fires on submission)"]
    KV["Azure Key Vault\n(Function key for auth)"]
    AF["Azure Functions\n/api/process-response"]
    REG["Form Registry\n(field rules + de-id config)"]
    RAW["OneLake Raw Layer\n(All fields, unmodified PHI)"]
    DEID(["De-identification\nhash | redact | generalize | encrypt"])
    CUR["OneLake Curated Layer\n(De-identified data)"]
    PBI["Power BI\n(DirectLake dashboards)"]
    ALERT["Outlook Alert Email\n(Failure notification)"]

    Forms --> PA
    PA -- "Retrieve response details" --> Forms
    KV -. "Function key" .-> PA
    PA -- "HTTP POST\nform_id + raw_response" --> AF
    AF -- "Look up field rules" --> REG
    AF -- "Write raw response" --> RAW
    AF --> DEID
    DEID -- "Write de-identified response" --> CUR
    CUR --> PBI
    AF -- "HTTP 200 OK" --> PA
    PA -. "On failure" .-> ALERT

    classDef primary fill:#4dabf7,stroke:#1864ab,color:#1a1a2e
    classDef success fill:#69db7c,stroke:#2b8a3e,color:#1a1a2e
    classDef warning fill:#ffd43b,stroke:#e67700,color:#1a1a2e
    classDef danger fill:#ff8787,stroke:#c92a2a,color:#1a1a2e
    classDef info fill:#b197fc,stroke:#6741d9,color:#1a1a2e
    classDef neutral fill:#ced4da,stroke:#495057,color:#1a1a2e

    class Forms,PA primary
    class AF,REG info
    class RAW,CUR,PBI success
    class DEID warning
    class ALERT danger
```

**Key points:**
- Power Automate authenticates to Azure Functions using a **function key** retrieved from Key Vault
- De-identification happens **inside** Azure Functions — between the raw write and curated write
- On failure, Power Automate sends an **Outlook alert email** to the configured admin address
- Power BI uses **DirectLake mode** — it queries OneLake directly with no ETL or data copy

---

## Self-Service Registration Flow

Clinicians register new forms through a simple 3-question intake form. The system automatically creates a per-form Power Automate data flow.

```mermaid
flowchart LR
    INTAKE["Registration\nIntake Form\n(3 questions)"]
    REGFLOW["Registration\nPower Automate Flow"]
    REGAPI["Azure Functions\n/api/register-form"]
    REGISTRY["Form Registry\n(new entry created)"]
    FLOWAPI["Flow Management API\n(creates per-form flow)"]
    PERFLOW["Per-Form\nData Flow\n(ready to process)"]

    PHI_CHECK{"Has PHI?"}
    PENDING["Status:\npending_review"]
    ACTIVE["Status:\nactive"]
    IT_REVIEW["IT Admin Reviews\n/api/activate-form"]

    INTAKE --> REGFLOW
    REGFLOW -- "HTTP POST\nform_url, name, has_phi" --> REGAPI
    REGAPI --> REGISTRY
    REGAPI --> PHI_CHECK
    PHI_CHECK -- "No" --> ACTIVE
    PHI_CHECK -- "Yes" --> PENDING
    PENDING --> IT_REVIEW
    IT_REVIEW -- "Classify fields,\nset de-id methods" --> ACTIVE
    ACTIVE --> REGAPI
    REGAPI -- "flow_create_body" --> REGFLOW
    REGFLOW -- "HTTP POST" --> FLOWAPI
    FLOWAPI --> PERFLOW

    classDef primary fill:#4dabf7,stroke:#1864ab,color:#1a1a2e
    classDef success fill:#69db7c,stroke:#2b8a3e,color:#1a1a2e
    classDef warning fill:#ffd43b,stroke:#e67700,color:#1a1a2e
    classDef danger fill:#ff8787,stroke:#c92a2a,color:#1a1a2e
    classDef info fill:#b197fc,stroke:#6741d9,color:#1a1a2e
    classDef neutral fill:#ced4da,stroke:#495057,color:#1a1a2e

    class INTAKE,REGFLOW primary
    class REGAPI,FLOWAPI info
    class REGISTRY,PERFLOW success
    class PHI_CHECK,PENDING warning
    class IT_REVIEW danger
    class ACTIVE success
```

**Key points:**
- Clinicians answer 3 questions: form URL, short description, and whether it contains patient info
- Forms flagged with PHI enter **pending_review** — they cannot process submissions until IT activates them
- IT classifies each field with a de-identification method (hash, redact, generalize, encrypt, or none)
- Once activated, the per-form Power Automate flow begins processing submissions automatically

---

## Security and Identity

Every connection between components uses a specific authentication method. No credentials are stored in code.

```mermaid
flowchart TD
    subgraph M365["Microsoft 365"]
        FORMS["Microsoft Forms"]
        PA["Power Automate"]
        OUTLOOK["Outlook\n(Alert emails)"]
    end

    subgraph AZURE["Azure Platform"]
        AF["Azure Functions\n(System Managed Identity)"]
        KV["Azure Key Vault"]
        STORAGE["Azure Storage"]
        AI["Application Insights"]
    end

    subgraph FABRIC["Microsoft Fabric"]
        ONELAKE["OneLake\n(Raw + Curated)"]
        PBI["Power BI"]
        WKSP["Fabric Workspace\n(Entra ID RBAC)"]
    end

    subgraph ENTRA["Microsoft Entra ID"]
        MI["Managed Identity"]
        RBAC["Workspace Roles"]
    end

    FORMS -- "M365 connector" --> PA
    PA -- "Function key\n(from Key Vault)" --> AF
    PA -- "M365 connector" --> OUTLOOK

    AF -- "Managed Identity" --> KV
    AF -- "Managed Identity" --> STORAGE
    AF -- "Managed Identity\n+ Bearer Token" --> ONELAKE
    AF -- "SDK integration" --> AI

    MI -. "Authenticates" .-> AF
    RBAC -. "Controls access" .-> WKSP

    WKSP --> ONELAKE
    ONELAKE --> PBI

    classDef primary fill:#4dabf7,stroke:#1864ab,color:#1a1a2e
    classDef success fill:#69db7c,stroke:#2b8a3e,color:#1a1a2e
    classDef warning fill:#ffd43b,stroke:#e67700,color:#1a1a2e
    classDef danger fill:#ff8787,stroke:#c92a2a,color:#1a1a2e
    classDef info fill:#b197fc,stroke:#6741d9,color:#1a1a2e
    classDef neutral fill:#ced4da,stroke:#495057,color:#1a1a2e

    class FORMS,PA,OUTLOOK primary
    class AF,KV,STORAGE,AI info
    class ONELAKE,PBI,WKSP success
    class MI,RBAC warning
```

### Authentication Methods Summary

| Connection | Method | Details |
|---|---|---|
| Power Automate → Azure Functions | **Function Key** | Stored in Key Vault as `function-app-key`. Rotatable via `rotate_function_key.py`. |
| Azure Functions → Key Vault | **Managed Identity** | System-assigned. `DefaultAzureCredential` in Python. No secrets in config. |
| Azure Functions → Azure Storage | **Managed Identity** | RBAC-based access to blob storage (form registry). |
| Azure Functions → OneLake | **Managed Identity + Bearer Token** | Token acquired via `DefaultAzureCredential`, passed to deltalake SDK. |
| Azure Functions → Fabric API | **Managed Identity + Bearer Token** | Scope: `https://api.fabric.microsoft.com/.default`. Used by RBAC auditor. |
| Power Automate → Forms | **M365 Connector** | Automatic via M365 tenant. User-delegated or service account connection. |
| Power Automate → Outlook | **M365 Connector** | Sends failure alert emails to admin address. |
| Fabric Workspace Access | **Entra ID RBAC** | Admin role → raw layer. Contributor/Viewer → curated layer. |

### Entra ID RBAC for Fabric

```mermaid
flowchart LR
    subgraph ROLES["Entra ID Roles"]
        ADMIN["IT Admin\n(Workspace Admin)"]
        LEAD["Department Lead\n(Contributor)"]
        ANALYST["Analyst\n(Viewer)"]
        CLINICIAN["Clinician\n(via Power BI RLS)"]
    end

    subgraph LAYERS["Fabric Lakehouse Layers"]
        RAW["Raw Layer\n(Full PHI - Restricted)"]
        CUR["Curated Layer\n(De-identified - Shared)"]
    end

    PBI["Power BI Reports\n(Row-Level Security)"]

    ADMIN -- "Full access" --> RAW
    ADMIN -- "Full access" --> CUR
    LEAD -- "Read access" --> CUR
    ANALYST -- "Read access" --> CUR
    CUR --> PBI
    CLINICIAN -- "Department-filtered" --> PBI

    classDef primary fill:#4dabf7,stroke:#1864ab,color:#1a1a2e
    classDef success fill:#69db7c,stroke:#2b8a3e,color:#1a1a2e
    classDef warning fill:#ffd43b,stroke:#e67700,color:#1a1a2e
    classDef danger fill:#ff8787,stroke:#c92a2a,color:#1a1a2e
    classDef info fill:#b197fc,stroke:#6741d9,color:#1a1a2e
    classDef neutral fill:#ced4da,stroke:#495057,color:#1a1a2e

    class ADMIN danger
    class LEAD,ANALYST info
    class CLINICIAN primary
    class RAW danger
    class CUR success
    class PBI success
```

---

## Two-Layer Data Model

Every form submission is written to **two layers** in the Fabric Lakehouse. The raw layer preserves all original data for audit and compliance. The curated layer contains only de-identified data for analytics.

```mermaid
flowchart TD
    SUBMIT["Form Submission\n(raw_response)"]

    subgraph RAW_LAYER["Raw Layer (Restricted)"]
        RAW_TABLE["table_name_raw\nAll fields unmodified\nFull PHI preserved"]
        RAW_ACCESS["Access: IT Admins only\nPurpose: Audit, compliance,\nreprocessing"]
    end

    subgraph DEID_ENGINE["De-Identification Engine"]
        HASH["hash: SHA-256 one-way\n(MRN, patient ID)"]
        REDACT["redact: Replace with REDACTED\n(names, emails)"]
        GENERAL["generalize: Reduce precision\n(age, dates, postal codes)"]
        ENCRYPT["encrypt: Reversible via Key Vault\n(authorized re-identification)"]
        NONE["none: Pass through unchanged\n(ratings, yes/no, counts)"]
    end

    subgraph CUR_LAYER["Curated Layer (Shared)"]
        CUR_TABLE["table_name_curated\nPHI removed or transformed\nSafe for analytics"]
        CUR_ACCESS["Access: Analysts, department leads\nPurpose: Dashboards, reporting"]
    end

    PBI["Power BI DirectLake\n(Near-real-time dashboards)"]

    SUBMIT --> RAW_TABLE
    SUBMIT --> DEID_ENGINE
    DEID_ENGINE --> CUR_TABLE
    CUR_TABLE --> PBI

    classDef primary fill:#4dabf7,stroke:#1864ab,color:#1a1a2e
    classDef success fill:#69db7c,stroke:#2b8a3e,color:#1a1a2e
    classDef warning fill:#ffd43b,stroke:#e67700,color:#1a1a2e
    classDef danger fill:#ff8787,stroke:#c92a2a,color:#1a1a2e
    classDef info fill:#b197fc,stroke:#6741d9,color:#1a1a2e
    classDef neutral fill:#ced4da,stroke:#495057,color:#1a1a2e

    class SUBMIT primary
    class RAW_TABLE,RAW_ACCESS danger
    class HASH,REDACT,GENERAL,ENCRYPT,NONE warning
    class CUR_TABLE,CUR_ACCESS success
    class PBI success
```

### De-Identification Methods

| Method | Transformation | Use Case | Example | Reversible? |
|---|---|---|---|---|
| **hash** | SHA-256 one-way hash | Direct identifiers requiring linkage (MRN, patient ID) | `"MRN-12345"` → `"a3f2b8c9d..."` | No |
| **redact** | Replace with `[REDACTED]` | Names, emails, free-text identifiers | `"John Smith"` → `"[REDACTED]"` | No |
| **generalize** | Reduce precision based on field type | Quasi-identifiers (age, postal code, date) | Age `35` → `"30-39"` | No |
| **encrypt** | Reversible encryption (Key Vault key) | Fields requiring authorized re-identification | Original value → encrypted blob | Yes |
| **none** | Pass through unchanged | Non-identifying data (counts, ratings, yes/no) | `"5"` → `"5"` | N/A |

### De-Identification Decision Tree

```mermaid
flowchart TD
    Q1{"Does this field contain\nPHI or PII?"}
    Q2{"Does it directly\nidentify a person?"}
    Q3{"Need to link\nrecords across forms?"}
    Q4{"Need the original\nvalue later?"}
    Q5{"Is aggregate\nanalysis needed?"}

    M_NONE["none\n(pass through)"]
    M_HASH["hash\n(SHA-256)"]
    M_ENCRYPT["encrypt\n(Key Vault)"]
    M_REDACT_D["redact\n(replace with placeholder)"]
    M_GENERAL["generalize\n(reduce precision)"]
    M_REDACT_Q["redact\n(replace with placeholder)"]

    Q1 -- "No" --> M_NONE
    Q1 -- "Yes" --> Q2
    Q2 -- "Yes (direct identifier)" --> Q3
    Q2 -- "No (quasi-identifier)" --> Q5
    Q3 -- "Yes" --> M_HASH
    Q3 -- "No" --> Q4
    Q4 -- "Yes" --> M_ENCRYPT
    Q4 -- "No" --> M_REDACT_D
    Q5 -- "Yes" --> M_GENERAL
    Q5 -- "No" --> M_REDACT_Q

    classDef primary fill:#4dabf7,stroke:#1864ab,color:#1a1a2e
    classDef success fill:#69db7c,stroke:#2b8a3e,color:#1a1a2e
    classDef warning fill:#ffd43b,stroke:#e67700,color:#1a1a2e
    classDef danger fill:#ff8787,stroke:#c92a2a,color:#1a1a2e
    classDef info fill:#b197fc,stroke:#6741d9,color:#1a1a2e
    classDef neutral fill:#ced4da,stroke:#495057,color:#1a1a2e

    class Q1,Q2,Q3,Q4,Q5 warning
    class M_NONE success
    class M_HASH,M_ENCRYPT info
    class M_REDACT_D,M_REDACT_Q danger
    class M_GENERAL primary
```

---

*Last updated: 2026-03-25. See [architecture.md](architecture.md) for compliance details, disaster recovery, and network architecture.*
