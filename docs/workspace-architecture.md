# Workspace Architecture — Hybrid Model

> **Status:** Future-state reference only (not implemented in the current POC)
> **Decision:** D-017 — Document architecture for future implementation
> **Date:** 2026-03-07
> **Current implementation:** The deployed POC still writes raw and curated tables to a single Fabric workspace and Lakehouse as documented in [Architecture](architecture.md).

---

## Overview

The hybrid workspace model separates raw PHI data from curated de-identified data using different Fabric workspaces with different access controls. This document describes a future design target, not the workflow implemented by the current Azure Functions, registry schema, or setup scripts.

```
┌─────────────────────────────────────────────┐
│  Central Raw Workspace (IT Admins only)     │
│                                             │
│  raw_lakehouse                              │
│  ├── formA_raw (all fields, full PHI)       │
│  ├── formB_raw                              │
│  └── formC_raw                              │
│                                             │
│  Access: IT Admins = Admin                  │
│          Function App MI = Contributor      │
│          Clinicians = NO ACCESS             │
└─────────────────────────────────────────────┘
          │
          │  Azure Function writes raw data here
          │  (always, regardless of PHI classification)
          │
          ▼
┌─────────────────────────────────────────────┐
│  Per-Clinician Curated Workspaces           │
│                                             │
│  "Forms — Dr. Smith"                        │
│  ├── curated_lakehouse                      │
│  │   ├── patient_survey_curated             │
│  │   └── intake_form_curated                │
│  └── Power BI reports                       │
│                                             │
│  Access: Dr. Smith = Viewer                 │
│          Function App MI = Contributor      │
│          IT Admins = Admin                  │
│                                             │
│  "Forms — Dr. Jones"                        │
│  ├── curated_lakehouse                      │
│  │   └── staff_feedback_curated             │
│  └── Power BI reports                       │
│                                             │
│  Access: Dr. Jones = Viewer                 │
│          Function App MI = Contributor      │
│          IT Admins = Admin                  │
└─────────────────────────────────────────────┘
```

---

## How It Works

### Registration Flow
1. Clinician submits registration form (form URL, description, PHI flag)
2. Azure Function registers the form in the blob registry
3. Azure Function calls Fabric REST API to:
   a. Find or create workspace: `"Forms — {submitter_name}"`
   b. Find or create Lakehouse: `curated_lakehouse`
   c. Grant the clinician Viewer role
   d. Grant the Function App managed identity Contributor role
4. PA Management connector creates the data pipeline flow
5. Clinician receives confirmation email with workspace link

### Data Processing Flow
1. Form response submitted → PA trigger fires
2. Azure Function processes the response:
   - **Raw write** → always goes to the central raw workspace/lakehouse
   - **Curated write** → goes to the clinician's personal workspace/lakehouse
   - Only classified + de-identified fields appear in curated
3. Clinician opens their workspace → sees dashboards with de-identified data

### PHI Protection
- **Raw workspace** is restricted to IT Admins — clinicians never see full PHI
- **Curated workspace** only contains de-identified data
- Unclassified fields are excluded from curated (quarantine pattern)
- Even if a clinician has Viewer access, they only see de-identified versions

---

## Data Routing

The Azure Function needs to know where to write curated data. This is stored in the form registry:

```json
{
  "form_id": "abc123",
  "form_name": "Patient Survey",
  "target_table": "patient_survey",
  "status": "active",
  "submitter_email": "dr.smith@org.com",
  "raw_workspace_id": "central-raw-workspace-guid",
  "raw_lakehouse_id": "central-raw-lakehouse-guid",
  "curated_workspace_id": "dr-smith-workspace-guid",
  "curated_lakehouse_id": "dr-smith-lakehouse-guid",
  "fields": [...]
}
```

The `register-form` endpoint populates these IDs during registration by calling the Fabric REST API.

---

## Permissions Model

| Role | Central Raw Workspace | Per-Clinician Workspace |
|------|----------------------|------------------------|
| **IT Admins** | Admin | Admin |
| **Function App MI** | Contributor | Contributor |
| **Clinician (owner)** | No access | Viewer |
| **Other clinicians** | No access | No access |
| **RBAC Audit Function** | Validates daily | Validates daily |

### Key Rules
1. Clinicians NEVER have access to the raw workspace
2. Each clinician only has access to their OWN curated workspace
3. The Function App is the only entity that writes to both
4. IT Admins can see everything for compliance/audit
5. The RBAC audit function verifies these rules daily

---

## Implementation Requirements

### Code Changes
1. **register-form handler** — After registration, call Fabric REST API to:
   - Create workspace: `POST /v1/workspaces` with name `"Forms — {submitter}"`
   - Create Lakehouse: `POST /v1/workspaces/{id}/items` type=Lakehouse
   - Assign roles: `POST /v1/workspaces/{id}/roleAssignments`
   - Store workspace/lakehouse IDs in registry entry
2. **onelake.py writer** — Read workspace/lakehouse IDs from form config instead of environment variables
3. **Form registry schema** — Add `submitter_email`, `raw_workspace_id`, `raw_lakehouse_id`, `curated_workspace_id`, `curated_lakehouse_id`

### Infrastructure
1. Central raw workspace + lakehouse (created during initial setup)
2. Fabric capacity must support multiple workspaces (F2+ should work)
3. Function App managed identity needs permissions to create workspaces (Fabric Admin role or delegated)

### Fabric API Calls Needed
```
POST /v1/workspaces                              — Create workspace
POST /v1/workspaces/{id}/items                   — Create Lakehouse
POST /v1/workspaces/{id}/roleAssignments         — Add Viewer role
POST /v1/workspaces/{id}/assignToCapacity        — Assign capacity
```

These are the same APIs already used in `Setup-FabricWorkspace.ps1`.

---

## Current State vs. Future State

| Aspect | Current (POC) | Future (Hybrid) |
|--------|--------------|-----------------|
| **Workspaces** | 1 workspace, 2 layers in same Lakehouse | 1 central raw + N per-clinician curated |
| **PHI isolation** | RBAC on layers within same workspace | Physical workspace separation |
| **Clinician access** | Shared workspace, row-level security | Own workspace, full Viewer access |
| **Workspace creation** | Manual or scripted | Auto-created during registration |
| **Complexity** | Low | Medium-High |
| **Scalability** | Limited by single workspace capacity | Each workspace independently manageable |

---

## Risks and Considerations

1. **Workspace proliferation** — At scale (100+ clinicians), many workspaces need management
2. **Capacity allocation** — Each workspace consumes Fabric capacity units
3. **Cross-workspace reporting** — Aggregating data across clinician workspaces requires a central reporting model (shortcuts or linked tables)
4. **Workspace cleanup** — Need a process to archive/delete workspaces when clinicians leave
5. **Fabric API rate limits** — Creating workspaces during registration adds latency (~5-10s per API call)
6. **Permissions complexity** — More workspaces = more RBAC to audit

---

## Migration Path

To implement this from the current POC:

1. Create the central raw workspace (can reuse existing workspace for raw)
2. Update `register-form` to create per-clinician workspaces via Fabric API
3. Update `onelake.py` to read workspace/lakehouse IDs from form config
4. Update the form registry schema with workspace fields
5. Migrate existing data from single workspace to the hybrid model
6. Update the RBAC audit function to check per-clinician workspaces

This can be done incrementally — the current single-workspace model continues to work while the hybrid model is built alongside it.
