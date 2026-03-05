# Administrative Overhead — Assessment & Remediation

> **Generated:** 2026-03-05
> **Status:** ✅ All remediations implemented
> **Severity Scale:** P0 (critical, immediate risk), P1 (high, significant burden), P2 (medium, nice-to-have)

---

## Executive Summary

An assessment of the Forms-to-Fabric pipeline identified **32 manual touchpoints** across four operational domains. Before remediation, the solution required **~90 minutes of admin work per new form** and **~50–65 hours/year** for 5 forms in production. After implementing automated solutions for the top 5 gaps, projected admin burden drops to **~15 minutes per form** and **~10–15 hours/year**.

---

## Full Administrative Touchpoint Inventory

### Domain 1: Onboarding a New Form (12 touchpoints)

| # | Step | Actor | Skill Level | Est. Time | Automated? | Risk |
|---|------|-------|-------------|-----------|------------|------|
| 1 | Extract Form ID from Forms URL | Clinician/Admin | Non-technical | 2 min | ✅ Graph API | Low |
| 2 | Create entry in form-registry.json | IT Admin | Semi-technical | 10 min | ✅ `manage_registry.py add-form` | ~~Medium~~ → Low |
| 3 | Map question IDs to fields | IT Admin | Semi-technical | 15 min | ✅ `manage_registry.py add-field` | ~~High~~ → Low |
| 4 | Classify field sensitivity levels | Privacy Officer | Semi-technical | 10–20 min | ⚠️ Guided by decision tree | Critical — human judgment needed |
| 5 | Select de-identification method | Privacy Officer/Admin | Semi-technical | 5–10 min | ⚠️ Decision tree in admin guide | High — PHI exposure if wrong |
| 6 | Deploy config via `azd deploy` | DevOps/IT Admin | Developer | 3 min | ✅ CI/CD auto-deploys on push | ~~Medium~~ → Low |
| 7 | Commit to Git | IT Admin | Developer | 2 min | ✅ Standard Git workflow | Low |
| 8 | Create Power Automate flow | IT Admin | Semi-technical | 15 min | ✅ `generate-flow` endpoint → import | ~~Medium~~ → Low |
| 9 | Retrieve & insert function key | IT Admin | Semi-technical | 3 min | ✅ Key Vault connector (auto) | ~~High~~ → Eliminated |
| 10 | Add "Get response details" action | IT Admin | Semi-technical | 5 min | ✅ Included in generated flow | ~~Medium~~ → Eliminated |
| 11 | Configure error notification email | IT Admin | Non-technical | 2 min | ✅ Included in generated flow | Low |
| 12 | Submit test response & validate | Clinician/Admin | Non-technical | 10 min | ⚠️ Still manual (E2E test) | Medium |

**Before remediation:** ~90 min/form · **After remediation:** ~15 min/form (steps 4, 5, 12 remain manual)

### Domain 2: Ongoing Maintenance (10 touchpoints)

| # | Task | Frequency | Est. Time | Automated? | Risk |
|---|------|-----------|-----------|------------|------|
| 1 | Rotate function app host key | 90 days | 10 min | ✅ `rotate_function_key.py` + Key Vault | ~~High~~ → Low |
| 2 | Rotate service principal secret | 90 days | 10 min | ⚠️ Manual (Azure AD) | High |
| 3 | Review Application Insights alerts | Daily | 5 min | ⚠️ Automated alerts, triage manual | High |
| 4 | Monitor Fabric capacity usage | Weekly | 5 min | ⚠️ Auto-alert possible | Medium |
| 5 | Check Power Automate flow run history | Weekly | 5 min | ⚠️ Alerting exists, review manual | High |
| 6 | Handle schema changes (form modifications) | Ad hoc | 30–60 min | ✅ `monitor_schema` detects automatically | ~~Critical~~ → Medium |
| 7 | Update form-registry.json for schema changes | Ad hoc | 15 min | ✅ `manage_registry.py` validates | ~~Critical~~ → Low |
| 8 | Redeploy after schema changes | Ad hoc | 3 min | ✅ CI/CD | ~~High~~ → Low |
| 9 | Manage access to Raw vs. Curated layers | As needed | 5 min | ✅ `audit_rbac` detects violations | ~~Critical~~ → Low |
| 10 | Investigate failed executions | As needed | 15–30 min | ⚠️ KQL queries speed up diagnosis | High |

### Domain 3: User Management (6 touchpoints)

| # | Step | Frequency | Est. Time | Automated? | Risk |
|---|------|-----------|-----------|------------|------|
| 1 | Grant workspace access to department | Per department | 3 min | ⚠️ Manual (Fabric portal) | High — wrong role = PHI exposure |
| 2 | Assign Contributor role to Function App identity | Once per deploy | 5 min | ✅ Bicep template | ~~Critical~~ → Eliminated |
| 3 | Assign Viewer role to clinicians | Per user | 2 min | ⚠️ Could use Azure AD groups | Low |
| 4 | Assign Contributor role to report creators | Per person | 2 min | ⚠️ Could use Azure AD groups | Low |
| 5 | Restrict Raw layer access to IT Admins only | Per workspace | 5 min | ✅ `audit_rbac` verifies daily | ~~Critical~~ → Low |
| 6 | Update error notification email | When contact changes | 2 min | ⚠️ Manual | Low |

### Domain 4: Troubleshooting (4 scenarios)

| Scenario | Diagnostic Steps | Est. Time | Automated? |
|----------|------------------|-----------|------------|
| Flow fails with 401 Unauthorized | Check Key Vault secret → rotate key → flows auto-update | 5 min | ✅ Key Vault connector eliminates this |
| Data not in Lakehouse | Check PA run history → App Insights → managed identity → registry | 20–30 min | ⚠️ KQL queries + troubleshooting flowchart help |
| De-identification not applied | Review registry config → App Insights → curated layer → redeploy | 15 min | ⚠️ Manual investigation |
| Function timeout (504) | Check payload size → execution duration → upgrade plan | 30 min–2 hrs | ⚠️ Metrics visible, decision manual |

---

## Annual Administrative Burden Summary

| Metric | Before Remediation | After Remediation | Δ |
|--------|-------------------|-------------------|---|
| **New form onboarding** | ~90 min | ~15 min | **−83%** |
| **Annual admin hours (5 forms)** | 50–65 hrs | 10–15 hrs | **−75%** |
| **Schema change detection** | None (silent failures) | Automated every 6 hrs | **Risk eliminated** |
| **RBAC compliance** | Manual, unverified | Audited daily at 8 AM | **Risk eliminated** |
| **Key rotation impact** | All flows break | Zero downtime | **Outage eliminated** |
| **Registry edit errors** | Common (hand-edited JSON) | Near-zero (CLI validated) | **Risk eliminated** |

### Remaining Manual Effort (cannot be automated)

These steps require human judgment and will always be manual:

1. **Sensitivity classification** — Deciding which fields contain PHI requires clinical/privacy expertise
2. **De-identification method selection** — Choosing hash vs. redact vs. generalize depends on use case
3. **End-to-end validation** — Submitting a test response and visually verifying dashboard output
4. **Service principal rotation** — Azure AD credential management
5. **Troubleshooting diagnosis** — Interpreting errors requires human judgment (though KQL queries accelerate this)

---

## Remediation Implementation Details

All five automation gaps have been **implemented, tested, and documented**:

| # | Gap | Severity | Risk | Annual Impact (5 forms) |
|---|-----|----------|------|------------------------|
| 1 | No schema change detection | **P0** | Silent data loss when clinicians modify forms | 10–15 hrs |
| 2 | No raw layer RBAC enforcement | **P0** | Accidental PHI exposure | Compliance violation |
| 3 | Manual Power Automate flow creation | **P1** | 15 min/form, error-prone | 5–8 hrs |
| 4 | Key rotation breaks flows | **P1** | Auth failures after rotation | 3–5 hrs |
| 5 | Hand-edited form-registry.json | **P1** | One typo breaks all forms | 5–10 hrs |

---

## Gap 1: Form Schema Change Detection (P0)

### Current State
When a clinician adds, removes, or renames questions in their Microsoft Form, the pipeline has **no way to detect the change**. The Azure Function continues processing with the stale `form-registry.json` configuration, resulting in:
- New questions being silently dropped (not captured in Lakehouse)
- Removed questions producing null values without alerting anyone
- Renamed questions potentially misclassified for de-identification

### Impact
- **Data loss**: New questions not captured until admin manually updates the registry
- **Compliance risk**: A new PHI field could go undetected and flow to the curated layer without de-identification
- **Operational burden**: Relies on clinicians remembering to notify IT — unreliable

### Remediation: Timer-Triggered Schema Monitor
**Solution:** A new Azure Function (`monitor_schema`) runs on a timer (every 6 hours) and:
1. Calls the Microsoft Graph API to retrieve the current question list for each registered form
2. Compares against the field definitions in `form-registry.json`
3. If differences are detected:
   - Logs a warning to Application Insights
   - Sends an email alert to the form owner and IT admin
   - Creates a structured diff report showing added/removed/changed questions
4. Optionally: auto-adds new questions with `sensitivity: "unclassified"` and `method: "redact"` (safe default — blocks unreviewed fields from curated layer)

**Files:** `src/functions/monitor_schema/`, `src/functions/shared/graph_client.py`

---

## Gap 2: Raw Layer RBAC Enforcement (P0)

### Current State
The pipeline writes PHI to the Lakehouse raw layer. Access control is entirely manual:
- An admin must remember to restrict raw layer access to IT admins only
- No automated check verifies this was done correctly
- No alert fires if someone grants a clinician access to the raw layer
- A single misconfigured workspace role exposes PHI to unauthorized users

### Impact
- **HIPAA violation risk**: PHI exposure to unauthorized personnel
- **Audit failure**: No evidence that access controls are enforced programmatically
- **Human error**: Every new workspace, every new user, every access change is a risk

### Remediation: RBAC Audit Function
**Solution:** A new Azure Function (`audit_rbac`) runs daily and:
1. Uses the Fabric REST API to enumerate workspace role assignments
2. Checks that the raw layer tables/folders are only accessible by members of the `IT-Admins` security group
3. Flags any non-admin users who have Contributor or higher access to the workspace
4. Generates an audit report stored in the Lakehouse (itself auditable)
5. Sends alerts for violations

**Files:** `src/functions/audit_rbac/`, `src/functions/shared/fabric_client.py`

---

## Gap 3: Power Automate Flow Provisioning (P1)

### Current State
Every new form requires manually creating a Power Automate flow through the UI:
1. Create automated cloud flow → select Forms trigger → select form
2. Add "Get response details" action
3. Add HTTP action with function URL + key + JSON body
4. Add error handling condition + email notification
5. Save and test

This takes ~15 minutes per form and is error-prone (wrong form ID, wrong URL, missing headers).

### Impact
- **Time cost**: 15 min × N forms
- **Error rate**: Wrong function key, wrong form_id, missing Content-Type header
- **Consistency**: Each flow is hand-built, leading to drift between flows

### Remediation: Flow Definition Generator
**Solution:** An admin API endpoint (`/api/generate_flow`) that:
1. Accepts a `form_id` and returns a complete Power Automate flow definition JSON
2. Pre-populates the trigger, response details action, HTTP call with correct URL/key/body, and error handling
3. Admin imports the generated JSON into Power Automate (single click import vs. multi-step manual creation)
4. Reduces creation from 15 min to 2 min with near-zero error rate

**Files:** `src/functions/generate_flow/`, updated `power-automate/flow-template.json`

---

## Gap 4: Key Rotation Synchronization (P1)

### Current State
Function keys are rotated every 90 days (security policy). After rotation:
1. The old key embedded in every Power Automate flow becomes invalid
2. **Every flow fails with 401 Unauthorized** until manually updated
3. Admin must edit each flow individually to paste the new key
4. During the gap, form responses are lost (Power Automate retries, but eventually gives up)

### Impact
- **Service outage**: All forms stop processing simultaneously during key rotation
- **Data loss**: Responses submitted during the outage window may be permanently lost
- **Scale problem**: With N forms, admin must update N flows — each taking 3–5 minutes

### Remediation: Key Vault–Referenced Authentication
**Solution:** Instead of hardcoding function keys in Power Automate:
1. Store the function key in Azure Key Vault as a secret
2. Power Automate uses the **Azure Key Vault connector** to retrieve the key at runtime
3. When keys are rotated, only the Key Vault secret is updated — all flows automatically pick up the new key
4. Enable Key Vault auto-rotation policy for the function key
5. Add documentation and a helper script for the rotation process

**Files:** Updated `infra/modules/key-vault.bicep`, `docs/admin-guide.md` (rotation section), `scripts/rotate_function_key.py`

---

## Gap 5: Form Registry Management (P1)

### Current State
`config/form-registry.json` is hand-edited raw JSON:
- No schema validation — a missing comma breaks the entire pipeline
- No field auto-discovery — admin must manually look up question IDs from the Forms URL
- No duplicate detection — same form_id can be entered twice
- No sensitivity classification guidance beyond a text-based decision tree
- Deployment requires `git commit` + `azd deploy` — a developer workflow for what should be an admin task

### Impact
- **Pipeline outage**: A single JSON syntax error breaks processing for ALL forms
- **Time cost**: 10–15 min per form for manual JSON editing and field mapping
- **Error rate**: High — JSON is unforgiving of typos
- **Skill barrier**: Requires developer-level comfort with JSON, Git, and CLI tools

### Remediation: Registry Management CLI
**Solution:** A Python CLI tool (`scripts/manage_registry.py`) that:
1. `add-form` — Interactively adds a new form: prompts for form_id, auto-discovers questions via Graph API, guides sensitivity classification, validates JSON, writes to registry
2. `validate` — Validates the entire registry against a JSON schema (catches syntax errors, missing fields, duplicate form_ids)
3. `list` — Lists all registered forms with status summary
4. `diff` — Compares registry against live form structure (supports Gap 1)
5. `update-form` — Updates an existing form's configuration interactively

**Files:** `scripts/manage_registry.py`, `config/form-registry.schema.json`

---

## Implementation Priority

All phases are **complete**:

```
Phase 1 (P0) ✅ DONE:
  ├── Schema Change Detector (Gap 1) — monitor_schema function
  └── RBAC Audit Function (Gap 2) — audit_rbac function

Phase 2 (P1) ✅ DONE:
  ├── Registry Management CLI (Gap 5) — scripts/manage_registry.py
  ├── Key Rotation Automation (Gap 4) — scripts/rotate_function_key.py + Key Vault connector
  └── Flow Provisioning Helper (Gap 3) — generate-flow endpoint
```

## Impact After Remediation

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Form onboarding time | ~90 min | ~15 min | **83% reduction** |
| Annual admin hours (5 forms) | 50–65 hrs | 10–15 hrs | **75% reduction** |
| Schema change detection | Manual/none | Automated (6-hr cycle) | **Eliminates silent data loss** |
| RBAC audit | Manual/none | Automated (daily) | **Eliminates PHI exposure risk** |
| Key rotation downtime | All flows break | Zero downtime | **Eliminates outage window** |
| Registry edit errors | Common | Near-zero (validated) | **Eliminates pipeline-wide outages** |
