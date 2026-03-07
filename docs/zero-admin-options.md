# Zero-Admin Form Registration — Options Analysis

## Goal
When a clinician registers a form, responses should start flowing to Fabric **automatically** — no admin involvement, no manual Power Automate flow creation, no JSON imports.

## Current State
Registration works (form → `/api/register-form` → blob registry), but a **separate data pipeline PA flow must be created manually** for each form. This requires admin effort and is the primary remaining bottleneck.

## Constraint
Microsoft Forms has **no public API for webhooks or subscriptions**. The only way to get real-time form responses is through Power Automate's "When a new response is submitted" trigger, which must be bound to a specific form.

---

## Options

### Option A: PA Management Connector — Registration flow creates data flow
**How:** The registration Power Automate flow uses the "Create Flow" action (PA Management connector) to programmatically create a data pipeline flow for the registered form.

| Aspect | Detail |
|--------|--------|
| **Clinician effort** | Zero — submit registration form, done |
| **Admin effort** | Zero after initial setup |
| **How it works** | Registration flow → register-form API → generate-flow API → PA Management "Create Flow" action → new data flow is live |
| **Prerequisites** | Power Automate Premium license (Management connector is premium), Environment ID |
| **Complexity** | Medium — need to construct valid flow definition with connection references |
| **Reliability** | High — PA Management connector is stable, Microsoft-supported |
| **Limitation** | Created flows need valid connection references for Forms and HTTP connectors; the creating user's connections are used |

### Option B: Azure Function calls Dataverse API to create flow
**How:** The `/api/register-form` endpoint directly calls the Dataverse Web API (`POST /api/data/v9.2/workflows`) to create the flow programmatically.

| Aspect | Detail |
|--------|--------|
| **Clinician effort** | Zero |
| **Admin effort** | Zero after initial setup |
| **How it works** | register-form handler → generates flow definition → POSTs to Dataverse API → enables flow |
| **Prerequisites** | Service Principal with Dataverse permissions, flow must be in a Solution, Power Platform environment ID |
| **Complexity** | High — Dataverse auth, `clientdata` JSON format, connection references, enabling flow |
| **Reliability** | Medium — `clientdata` format is undocumented/fragile, connection references are environment-specific |
| **Limitation** | Only works for Solution-based flows; "My Flows" cannot be managed via API |

### Option C: Timer-based polling function (eliminate PA flows entirely)
**How:** An Azure Function runs on a timer (e.g., every 5 minutes), polls Microsoft Forms for new responses via Graph API or Excel export, and writes directly to Fabric.

| Aspect | Detail |
|--------|--------|
| **Clinician effort** | Zero — register and done |
| **Admin effort** | Zero — no PA flows at all |
| **How it works** | Timer function → for each registered form → poll for new responses → process → write to Fabric |
| **Prerequisites** | Graph API access to Forms (limited), or Forms responses linked to Excel (via OneDrive API) |
| **Complexity** | Medium — need to track "last processed response" per form |
| **Reliability** | Low-Medium — Forms Graph API is limited/undocumented; Excel export approach adds latency |
| **Limitation** | **Microsoft Forms has no public Graph API for listing responses.** Would need to use the Excel-export workaround (Forms → Excel → OneDrive API → read new rows). Adds 5-15 min latency. |

### Option D: Single universal PA flow with dynamic form routing
**How:** One Power Automate flow handles ALL forms. When a response comes in, it calls the function with form_id and raw_response.

| Aspect | Detail |
|--------|--------|
| **Clinician effort** | Zero (if we can add forms to the trigger dynamically) |
| **Admin effort** | Zero |
| **How it works** | One flow with a Forms trigger that covers all forms → function routes by form_id |
| **Prerequisites** | A way to make one PA trigger fire for multiple forms |
| **Complexity** | Low IF possible |
| **Reliability** | High |
| **Limitation** | **Not possible.** The PA Forms trigger requires selecting a specific form. There is no "any form" trigger. Each form needs its own trigger. |

### Option E: Registration flow emails clinician a "one-click import" link
**How:** After registration, the PA flow calls `/api/generate-flow`, saves the JSON to SharePoint, and emails the clinician a deep link to import it into PA.

| Aspect | Detail |
|--------|--------|
| **Clinician effort** | ~2 min — click link, confirm import, save |
| **Admin effort** | Zero |
| **How it works** | Registration flow → generate-flow → save JSON → email with import link |
| **Prerequisites** | SharePoint site for hosting flow definitions |
| **Complexity** | Low |
| **Reliability** | High |
| **Limitation** | Not zero-effort — clinician still imports. But much better than manual creation. |

### Option F: Hybrid — PA creates flow + fallback email
**How:** Registration flow tries Option A (PA Management "Create Flow"). If that fails (licensing, permissions), falls back to Option E (email the import link).

| Aspect | Detail |
|--------|--------|
| **Clinician effort** | Zero (if Option A works), ~2 min fallback |
| **Admin effort** | Zero |
| **How it works** | Try "Create Flow" → if error → email import link |
| **Complexity** | Medium |
| **Reliability** | High (graceful degradation) |

---

## Recommendation

> **Status:** Option A has been implemented. See the registration flow setup in [setup-guide.md](setup-guide.md) Step 4.

**Option A (PA Management Connector)** is the best path if Premium licensing is available. It's:
- Zero-effort for clinicians
- Zero-effort for admins
- Uses a supported Microsoft connector
- The `generate-flow` endpoint already produces the flow definition

**If Premium isn't available**, Option E (email with import link) is the pragmatic fallback — ~2 min clinician effort.

**Option F (hybrid)** gives the best of both worlds and degrades gracefully.

**Avoid Option B** (Dataverse API) — `clientdata` format is undocumented and fragile.
**Avoid Option C** (polling) — Forms has no public response API.
**Option D is impossible** — PA Forms trigger can't cover multiple forms.

---

## Implementation for Option A

The registration PA flow needs 2 additional steps after the `/api/register-form` call:

1. **HTTP GET** to `/api/generate-flow?form_id={form_id}` — gets the flow definition JSON
2. **"Create Flow"** action (PA Management connector):
   - Environment: current environment ID
   - Display Name: "Forms to Fabric — {form_name}"
   - Definition: output from step 1
   - State: Enabled

The `generate-flow` endpoint already exists and produces valid definitions. The main work is configuring the PA Management connector action with proper connection references.

### Prerequisites for Option A
1. Power Automate Premium license for the account running the registration flow
2. Environment Admin or Environment Maker role for the service account
3. Valid Forms and HTTP connection references in the environment
