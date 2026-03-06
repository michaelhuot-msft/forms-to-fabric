# Decisions Log

> **Audience:** IT Leadership, Project Stakeholders
> **Last Updated:** 2026-03-05


---

## Purpose

This log captures every significant design decision made during the Forms to Fabric project. It serves two purposes:

1. **Validation** — The customer can review each decision, confirm it matches their expectations, and flag anything that needs revisiting.
2. **Future reference** — When someone asks "why did we do it this way?", this document has the answer.

Decisions are numbered sequentially (D-001, D-002, …). Each entry records what was decided, why, what else was considered, and how to change it later if needs evolve.

---

## Decisions from Initial Planning

### D-001

| Field | Detail |
|-------|--------|
| **Decision** | Keep Microsoft Forms as the authoring tool for data-collection forms |
| **Date** | 2025-07 |
| **Context** | Clinicians already create and maintain their own Forms. Replacing Forms with a custom builder would require training, migration, and ongoing support. The goal is to meet users where they are. |
| **Alternatives considered** | Custom web form builder; Power Apps model-driven forms; SharePoint lists with custom forms |
| **How to change later** | The Azure Function already normalizes form responses into a standard schema. To support a different authoring tool, add a new ingestion adapter in the function without changing the Lakehouse or Power BI layers. |

---

### D-002

| Field | Detail |
|-------|--------|
| **Decision** | Assume PHI may be present in all data types and design accordingly |
| **Date** | 2025-07 |
| **Context** | Even forms that clinicians say contain no patient data could accidentally include identifiers. Designing the entire pipeline as PHI-capable from day one avoids a costly retrofit later. |
| **Alternatives considered** | Separate PHI and non-PHI pipelines; PHI handling as an add-on tier |
| **How to change later** | This is a security posture, not a technical constraint. If the organization later determines certain data categories are definitively non-PHI, access controls on those datasets can be relaxed without architectural changes. |

---

### D-003

| Field | Detail |
|-------|--------|
| **Decision** | Near-real-time data freshness (event-driven) rather than batch processing |
| **Date** | 2025-07 |
| **Context** | Clinicians expect to see submitted responses reflected in dashboards within minutes, not hours. Event-driven processing via Power Automate triggers provides this without polling or scheduled jobs. |
| **Alternatives considered** | Nightly batch ETL; hourly scheduled sync; manual export/import |
| **How to change later** | The Azure Function can be invoked on any schedule. To switch to batch, replace the Power Automate trigger with a Timer trigger and modify the function to pull all new responses since the last run. |

---

### D-004

| Field | Detail |
|-------|--------|
| **Decision** | Use Microsoft Fabric Lakehouse as the analytical destination (recommended over Warehouse) |
| **Date** | 2025-07 |
| **Context** | Lakehouse supports both structured and semi-structured data, uses Delta Lake for ACID transactions, and integrates natively with Power BI via DirectLake mode. Warehouse would work but adds SQL-only constraints that limit flexibility for evolving form schemas. |
| **Alternatives considered** | Fabric Warehouse (SQL-only); Azure SQL Database; Dataverse |
| **How to change later** | Data lands as Delta tables. To migrate to a Warehouse, create views or shortcuts over the existing Delta tables — no data duplication required. |

---

### D-005

| Field | Detail |
|-------|--------|
| **Decision** | Start small and scale — pilot with 1–3 forms before organization-wide rollout |
| **Date** | 2025-07 |
| **Context** | A phased approach lets the team validate the pipeline end-to-end, gather clinician feedback, and refine the process before supporting dozens of forms. It also limits blast radius if something goes wrong. |
| **Alternatives considered** | Big-bang rollout to all existing forms; department-by-department rollout |
| **How to change later** | Scaling is additive. Each new form is registered independently. No changes to the core pipeline are needed to grow from 3 to 300 forms. See [Pilot Program](pilot-program.md) for the rollout plan. |

---

### D-006

| Field | Detail |
|-------|--------|
| **Decision** | Power Automate as the event trigger + Azure Function for processing logic |
| **Date** | 2025-07 |
| **Context** | Power Automate is the only Microsoft tool that can trigger on Microsoft Forms submissions without polling. The Azure Function handles the heavy lifting (validation, transformation, Lakehouse writes) in Python, which is easier to test, version-control, and maintain than Power Automate expressions. |
| **Alternatives considered** | Power Automate only (no function); Logic Apps + Function; direct Graph API polling |
| **How to change later** | The function is HTTP-triggered and stateless. Any system that can make an HTTP POST with the correct payload can replace Power Automate as the trigger (e.g., Logic Apps, a custom webhook, or a Graph API subscription if Microsoft adds Forms support). |

---

### D-007

| Field | Detail |
|-------|--------|
| **Decision** | Require organizational Microsoft 365 accounts (no personal/consumer accounts) |
| **Date** | 2025-07 |
| **Context** | Organizational accounts enable Entra ID (Azure AD) authentication, conditional access policies, and compliance controls. Consumer accounts cannot access organizational Forms or meet healthcare compliance requirements. |
| **Alternatives considered** | Support both account types; guest access for external collaborators |
| **How to change later** | If external collaborators need to submit forms, use Entra ID B2B guest invitations. The pipeline does not need to change — guest users appear as organizational identities. |

---

### D-008

| Field | Detail |
|-------|--------|
| **Decision** | Two-layer data model: raw (restricted, full PHI) + curated (de-identified) |
| **Date** | 2025-07 |
| **Context** | Separating raw and curated layers lets the pipeline preserve original data for compliance and audit while providing a safe, de-identified dataset for analytics and self-service reporting. Role-based access controls restrict who can see each layer. |
| **Alternatives considered** | Single layer with column-level security; three layers (raw, cleansed, curated); de-identify in place |
| **How to change later** | Adding a third layer (e.g., an aggregated summary layer) is straightforward — create new Delta tables and Notebook transforms. The existing two layers remain untouched. |

---

### D-009

| Field | Detail |
|-------|--------|
| **Decision** | Include a self-service Power BI dashboard as part of the solution |
| **Date** | 2025-07 |
| **Context** | The primary value proposition is that clinicians can see their data in dashboards without waiting for IT to build reports. A pre-built Power BI template connected via DirectLake mode delivers instant value and demonstrates the pipeline's capability. |
| **Alternatives considered** | Clinicians build their own reports from scratch; export data to Excel; use Fabric notebooks for analysis |
| **How to change later** | The Power BI template is a starting point. Clinicians and analysts can duplicate it, customize visuals, or build entirely new reports against the same curated dataset. |

---

### D-010

| Field | Detail |
|-------|--------|
| **Decision** | Maintain as a public, reusable template repository with no client-identifying information |
| **Date** | 2025-07 |
| **Context** | The solution is designed as a shareable accelerator that any organization can fork and customize. Keeping the repo free of client names, URLs, and environment-specific secrets makes it safe to publish openly and reuse across engagements. The repository is published as a public proof-of-concept / reference implementation with no support commitments. |
| **Alternatives considered** | Client-specific repo with environment branches; monorepo with per-client folders |
| **How to change later** | If a specific deployment needs private customizations, fork the repo into a private repository. Environment-specific values live in `config/` files and environment variables — populate those config files without changing the shared codebase. |

---

## Decisions from Self-Service Registration

### D-011

| Field | Detail |
|-------|--------|
| **Decision** | Use a Microsoft Form as the registration intake mechanism |
| **Date** | 2025-07 |
| **Context** | Clinicians are already familiar with Microsoft Forms. Using a Form for registration means zero new tool adoption — they fill out the same kind of form they already use for data collection. Power Automate triggers natively on Form submissions, keeping the architecture consistent with the rest of the pipeline. |
| **Alternatives considered** | Power App (richer UI but requires app deployment and user training); Logic App with a custom web form (more flexible but adds a web-hosting dependency); SharePoint list with a custom form (familiar but harder to trigger reliably) |
| **How to change later** | The Azure Function `/api/register` endpoint accepts an HTTP POST with a standard payload. Replace the Form + Power Automate trigger with any system that can POST the same JSON (form link, description, PHI flag, submitter). |

---

### D-012

| Field | Detail |
|-------|--------|
| **Decision** | Automatic activation for non-PHI forms; IT approval required for PHI forms |
| **Date** | 2025-07 |
| **Context** | Most data-collection forms in this environment do not contain patient information. Requiring IT approval for every registration would create an unnecessary bottleneck. Automatic activation for non-PHI forms keeps the process fast, while the approval gate for PHI forms ensures proper field classification and access controls before sensitive data enters the pipeline. |
| **Alternatives considered** | Fully automatic (no approval for any form — risky for PHI); IT reviews every form (safe but slow and doesn't scale); clinician self-classifies fields (too error-prone for PHI) |
| **How to change later** | The PHI flag is evaluated in the Azure Function. To require approval for all forms, change the default status from `active` to `pending_review` regardless of the PHI flag. To go fully automatic, implement automated PHI detection (e.g., column-name pattern matching) and remove the approval step. |

---

### D-013

| Field | Detail |
|-------|--------|
| **Decision** | Clinicians indicate Yes/No for patient info; IT classifies specific PHI fields |
| **Date** | 2025-07 |
| **Context** | Clinicians know whether their form deals with patients but are not trained to classify individual fields against HIPAA categories. A simple Yes/No question is easy to answer and triggers the right workflow. IT then reviews the actual form fields and marks which ones contain PHI, ensuring accurate de-identification in the curated layer. |
| **Alternatives considered** | Clinicians tag each field as PHI/non-PHI during registration (error-prone); automated PHI detection using NLP (not reliable enough yet); IT classifies everything (bottleneck for non-PHI forms) |
| **How to change later** | Add an automated PHI classifier as a pre-screening step in the Azure Function. If the classifier is confident, skip IT review. If uncertain, flag for human review. The registry schema already supports per-field PHI metadata. |

---

### D-014

| Field | Detail |
|-------|--------|
| **Decision** | On form structure changes: detect, notify IT, keep form active, quarantine new fields in raw layer only |
| **Date** | 2025-07 |
| **Context** | Clinicians frequently tweak their forms (add a question, rename a column). Deactivating the form on every change would disrupt data collection. Instead, the Schema Monitor function detects changes, alerts IT, and quarantines new or modified fields — they appear in the raw (restricted) layer but are excluded from the curated (de-identified) layer until IT reviews and classifies them. Existing fields continue flowing normally. |
| **Alternatives considered** | Pause data collection on schema change (disruptive); auto-promote new fields to curated (risky for PHI); require clinicians to re-register after changes (confusing) |
| **How to change later** | The quarantine behavior is controlled by the Schema Monitor function. To auto-promote non-PHI fields, add a classification step that checks new field names against a known-safe list. To pause collection, change the function to set the form status to `pending_review` on schema change. |

---

### D-015

| Field | Detail |
|-------|--------|
| **Decision** | Provision Fabric capacity via Bicep and workspace/lakehouse via PowerShell script |
| **Date** | 2026-03 |
| **Context** | The setup guide originally required manual Fabric portal steps (create workspace, create Lakehouse, assign capacity, grant access). This was error-prone and not reproducible. Following a pattern from a reference project, we split provisioning into Bicep (capacity — ARM-supported) and PowerShell (workspace/lakehouse — REST API only, not ARM-supported). |
| **Alternatives considered** | Fully manual portal setup; Terraform with Fabric provider (immature); Python script using Fabric SDK (less ecosystem support than PowerShell for Azure ops) |
| **How to change later** | If Microsoft adds ARM/Bicep support for Fabric workspaces and lakehouses, consolidate the PowerShell script into the Bicep templates. Monitor the `Microsoft.Fabric` resource provider for new resource types. |

---

## How to Add a New Decision

Copy the template below and append it to the appropriate section:

```markdown
### D-0XX

| Field | Detail |
|-------|--------|
| **Decision** | What was decided |
| **Date** | YYYY-MM |
| **Context** | Why this decision was made |
| **Alternatives considered** | What else was evaluated |
| **How to change later** | What to do if this needs to change |
```

---

## Related Documents

- [Architecture](architecture.md) — System design shaped by these decisions
- [Registration Form Template](registration-form-template.md) — Implements D-011, D-012, D-013
- [Admin Guide](admin-guide.md) — Operational procedures
- [Pilot Program](pilot-program.md) — Implements D-005

---

## Lessons Learned

> **Added:** 2026-03-05 — After three rounds of automation (initial build → automation gaps → self-service registration)

### What Worked

| Lesson | Detail |
|--------|--------|
| **Forms-as-intake for a Forms pipeline** | Using Microsoft Forms as the registration intake means clinicians use the same tool for both data collection and pipeline registration. Zero new tools to learn. |
| **raw_response passthrough** | The single highest-error-rate step (manual question-ID-to-field mapping) was eliminated by the `raw_response` passthrough pattern. The Azure Function receives the entire Forms response and extracts answers at processing time — no Graph API needed. |
| **Quarantine pattern for unknown fields** | Writing unregistered fields to the raw layer but excluding them from curated balances data availability (no data loss) with PHI safety (no unclassified data in reports). |
| **Status model (active / pending_review)** | A simple two-state gate enables zero-touch onboarding for non-PHI forms while preserving a human-in-the-loop for PHI forms. The conditional approval path avoided an all-or-nothing trade-off. |
| **Iterative automation** | Three rounds of improvement (v1: manual, v2: CLI + monitoring, v3: self-service) each built on the last. This avoided big-bang risk and let us validate each layer before adding the next. |
| **Documentation-first approach** | Writing clinician guides and admin docs before code caught UX problems early and created alignment with stakeholders before implementation. |
| **Atomic commits and continuous push** | Every logical change was committed and pushed immediately, keeping the repo deployable at all times and making rollback trivial. |

### What Could Be Improved

| Area | Current Limitation | Potential Solution |
|------|-------------------|-------------------|
| **Registry storage** | JSON file on disk; works at low volume but fragile at scale | Move to Cosmos DB or a Fabric Lakehouse table for the registry |
| **One PA flow per form** | Creates N flows for N forms; admin overhead scales linearly | Use a single dynamic flow with form_id as parameter (requires Power Automate Premium) |
| **No automatic PA flow creation** | Admin still imports generated JSON into Power Automate UI | Power Automate Management Connector API could programmatically create flows |
| **Manual E2E testing** | Human must submit a test response and visually verify dashboard | Synthetic test: submit via Graph API, assert on Lakehouse table rows |
| **Field classification is manual** | IT must open the form and classify each field for PHI | NLP/regex-based pre-screening (e.g., "patient name" → auto-flag as direct identifier) |

### Design Principles That Emerged

1. **Meet users where they are** — Clinicians know Forms; don't ask them to learn a new tool. The admin CLI wraps complexity so IT also stays in familiar territory.
2. **Safe defaults over fast defaults** — When in doubt, restrict (quarantine unknown fields, require IT review for PHI). It's easier to open up later than to close down after a PHI leak.
3. **Automate detection before automation of action** — Schema monitor detects changes without auto-fixing them. This builds trust and gives IT visibility before we automate the response.
4. **Make the right thing the easy thing** — The `add-form --form-url` command does everything in one step. When the easy path is also the correct path, adoption follows naturally.
5. **Document decisions with alternatives** — Every choice records what else was considered and how to change later. This prevents re-litigation and enables future teams to evolve the architecture confidently.
