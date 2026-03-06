# Administrative Overhead — Assessment & Evolution

> **Last Updated:** 2026-03-05
> **Status:** ✅ Three rounds of automation applied
> **Revision:** 3 — Post–self-service registration

---

## Executive Summary

Three rounds of automation reduced manual touchpoints from **32 to 16** and onboarding time from **~90 min to ~11 min** (non-PHI) or **~20 min** (PHI). Annual admin burden for 5 forms in production dropped from **50–65 hrs to 10–15 hrs**. At 20 forms/year, estimated effort drops from **~130 hrs to ~25 hrs**.

---

## Evolution Timeline

| Phase | What Changed | Touchpoints | Onboarding Time | Annual Burden (5 forms) |
|-------|-------------|-------------|-----------------|------------------------|
| **v1: Initial build** | Manual CLI + JSON editing | 32 | ~90 min | 50–65 hrs |
| **v2: Automation gaps addressed** | Schema monitor, RBAC audit, registry CLI, key rotation, flow generator | 24 | ~15 min | 10–15 hrs |
| **v3: Self-service registration** | Registration form, raw_response passthrough, approval workflow, field quarantine | 16 | ~11 min (non-PHI) / ~20 min (PHI) | 10–15 hrs |

---

## Current Touchpoint Inventory (Post v3)

### Domain 1: Onboarding a New Form (12 original → 3 remaining manual)

| # | Original Step | v1 Time | Current Status | Current Time | What Changed |
|---|-------------|---------|----------------|--------------|--------------|
| 1 | Extract Form ID from URL | 2 min | **ELIMINATED** | 0 | Clinician submits link; `/api/register-form` extracts automatically |
| 2 | Create registry entry | 10 min | **ELIMINATED** | 0 | Auto-created by register-form endpoint |
| 3 | Map question IDs to fields | 15 min | **ELIMINATED** | 0 | raw_response passthrough extracts fields at runtime |
| 4 | Classify field sensitivity | 10-20 min | **Manual (PHI only)** | 5-10 min | Only for PHI forms; non-PHI skip entirely |
| 5 | Select de-id method | 5-10 min | **Manual (PHI only)** | 5-10 min | Only for PHI forms; guided by decision tree |
| 6 | Deploy config | 3 min | **ELIMINATED** | 0 | Register-form writes directly; no deploy needed |
| 7 | Git commit | 2 min | **ELIMINATED** | 0 | Function writes registry at runtime |
| 8 | Create Power Automate flow | 15 min | **ELIMINATED** | 0 | Registration flow handles this; generate-flow endpoint available for data pipeline flow |
| 9 | Retrieve function key | 3 min | **ELIMINATED** | 0 | Key Vault connector in all flow templates |
| 10 | Add response details action | 5 min | **ELIMINATED** | 0 | Included in generated flow definitions |
| 11 | Configure error notification | 2 min | **ELIMINATED** | 0 | Pre-configured in flow templates |
| 12 | End-to-end test | 10 min | **Manual** | 10 min | Still requires human verification of dashboard |

**Summary:** Non-PHI: 10 min (E2E test only). PHI: 20-25 min (classify + de-id + activate + test)

### Domain 2: Ongoing Maintenance (10 original → 5 remaining manual)

| # | Task | Frequency | Status | Current Time |
|---|------|-----------|--------|-------------|
| 1 | Function key rotation | 90 days | ✅ Automated | 0 min |
| 2 | Service principal rotation | 90 days | ⚠️ Manual | 10 min |
| 3 | Review App Insights alerts | Daily | ⚠️ Reduced | 3 min |
| 4 | Monitor Fabric capacity | Weekly | ⚠️ Reduced | 3 min |
| 5 | Check PA flow history | Weekly | ⚠️ Reduced | 3 min |
| 6 | Handle schema changes | Ad hoc | ✅ Automated (detect + quarantine) | 0 min |
| 7 | Update registry for changes | Ad hoc | ✅ Auto-quarantined | 5 min review |
| 8 | Redeploy after changes | Ad hoc | ✅ Eliminated | 0 min |
| 9 | RBAC access management | As needed | ✅ Automated audit | 0 min |
| 10 | Investigate failures | As needed | ⚠️ Reduced | 10-15 min |

### Domain 3: User Management (6 original → 4 remaining manual)

| # | Step | Status | Current Time |
|---|------|--------|-------------|
| 1 | Grant workspace access | ⚠️ Manual | 3 min | (Workspace creation is automated via `Setup-FabricWorkspace.ps1`) |
| 2 | Function App identity role | ✅ Bicep IaC | 0 min |
| 3 | Assign Viewer to clinicians | ⚠️ Manual | 1 min |
| 4 | Assign Contributor to creators | ⚠️ Manual | 1 min |
| 5 | Restrict raw layer | ✅ Daily audit | 0 min |
| 6 | Update notification email | ⚠️ Manual | 2 min |

### Domain 4: Troubleshooting (4 original → 3 remaining)

| Scenario | Status | Current Time |
|----------|--------|-------------|
| 401 Unauthorized | ✅ Eliminated (Key Vault) | 0 min |
| Data not in Lakehouse | ⚠️ Reduced (KQL + diagnostics) | 15-20 min |
| De-id not applied | ⚠️ Reduced (schema monitor alerts) | 10 min |
| Function timeout | ⚠️ Reduced (metrics visible) | 20 min |

---

## New Touchpoints from Self-Service (one-time + ongoing)

| Touchpoint | Frequency | Time | Notes |
|------------|-----------|------|-------|
| Set up registration form | Once | 15 min | Copy 3 questions into Microsoft Forms |
| Create registration PA flow | Once | 10 min | Import from template |
| Configure Teams notification | Once | 5 min | Set channel ID |
| Review PHI form submissions | Per PHI form | 5-10 min | Open form, review questions |
| Activate form after review | Per PHI form | 2 min | POST to /api/activate-form |

---

## Annual Burden Summary

| Metric | v1 (Initial) | v2 (Automation) | v3 (Self-service) | Δ Total |
|--------|-------------|-----------------|-------------------|---------|
| **Onboarding (non-PHI)** | ~90 min | ~15 min | **~11 min** | **−88%** |
| **Onboarding (PHI)** | ~90 min | ~15 min | **~20 min** | **−78%** |
| **Annual hours (5 forms)** | 50-65 hrs | 10-15 hrs | **10-15 hrs** | **−75%** |
| **Annual hours (20 forms)** | ~130 hrs | ~40 hrs | **~25 hrs** | **−81%** |
| **Manual touchpoints** | 32 | 24 | **16** | **−50%** |
| **Schema change response** | Undetected | Detected + alert | **Detected + quarantined** | **Risk eliminated** |
| **RBAC compliance** | Unverified | Daily audit | **Daily audit** | **Risk eliminated** |
| **Key rotation impact** | All flows break | Zero downtime | **Zero downtime** | **Risk eliminated** |

---

## Remaining Manual Steps (Cannot Be Automated)

These 16 touchpoints remain manual because they require human judgment, governance decisions, or platform limitations:

1. **Field sensitivity classification** — Requires clinical/privacy expertise
2. **De-identification method selection** — Context-dependent (hash vs redact vs generalize)
3. **End-to-end testing** — Visual verification of dashboard output
4. **Service principal rotation** — Azure AD/Entra limitation
5. **Workspace access grants** — Fabric portal manual assignment
6. **Clinician role assignment** — Manual or Azure AD group management
7. **Report creator role assignment** — Manual Fabric RBAC
8. **PHI form review** — Governance gate (intentional human-in-loop)
9. **Form activation after review** — Governance gate
10. **App Insights alert triage** — Human judgment for diagnosis
11. **PA flow health monitoring** — Human judgment for triage
12. **Fabric capacity monitoring** — Capacity planning decisions
13. **Failed execution investigation** — Case-by-case diagnosis
14. **Schema change review** — Verify change is intentional
15. **Notification email updates** — Low-frequency manual edit
16. **Error escalation decisions** — Human judgment on severity

---

## Remaining Friction Points (Next Automation Targets)

| Priority | Friction Point | Current State | Potential Automation | Effort | Impact |
|----------|---------------|---------------|---------------------|--------|--------|
| **P1** | Service principal rotation | Manual every 90 days | Entra ID workload identity federation (no secrets) | Medium | High — eliminates rotation entirely |
| **P1** | Schema change auto-classification | IT manually classifies new fields | NLP/regex-based PHI pre-screening ("name", "DOB", "MRN" → auto-flag) | Medium | High — could auto-classify 80%+ of new fields |
| **P2** | Workspace access grants | Manual Fabric portal (workspace provisioning is now IaC via `Setup-FabricWorkspace.ps1`) | Fabric REST API via Power Automate | High | Low — infrequent operation |
| **P2** | Clinician group management | Manual Azure AD | Entra ID dynamic groups based on department | Medium | Low — typically batch operation |
| **P2** | Error notification escalation | Email-only alerts | PagerDuty / Teams webhook integration | Low | Medium — reduces mean time to repair |
| **P3** | End-to-end test automation | Manual form submission + visual check | Synthetic test submission via Graph API + Lakehouse assertion | High | Low — testing is infrequent |

---

## Lessons Learned

### What Worked Well
1. **Forms-as-intake for a Forms pipeline** — Using the same tool (Microsoft Forms) for the registration meta-form means clinicians already know the interface
2. **raw_response passthrough** — Eliminated manual field mapping. The Azure Function extracts answers from the raw Forms response at processing time, so no per-question configuration is needed.
3. **Quarantine pattern** — Writing unknown fields to raw but excluding from curated balances data availability with PHI safety
4. **Status model (active/pending_review)** — Simple two-state gate enables self-service without compromising PHI governance
5. **Iterative automation** — Three rounds of improvement, each building on the last, avoided big-bang risk

### What Could Be Better
1. **Registry is a JSON file** — Works for low-volume, but at scale should move to a database (Cosmos DB or Fabric table)
2. **Power Automate flow per form** — Creates N flows for N forms; a single flow with dynamic form ID would be simpler but requires Premium connector
3. **No automatic PA flow creation** — Admin still imports a generated JSON; Power Automate's API doesn't support programmatic flow creation with Forms connector
4. **Manual E2E testing** — Still requires a human to submit a test response and visually verify the dashboard
