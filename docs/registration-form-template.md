# Registration Form Template — "Register Your Form for Analytics"

> **Audience:** IT Administrators
> **Last Updated:** 2026-03-05


---

## Overview

Clinicians across the organization author data-collection forms in Microsoft Forms. Before those forms can feed into the analytics pipeline, they must be **registered** — a lightweight process that tells the system *which* form to watch, *what* it does, and *whether* it contains patient information.

The **"Register Your Form for Analytics"** Microsoft Form is a **meta-form**: a form about forms. A clinician fills it out once per data-collection form they want connected to the Fabric Lakehouse and Power BI dashboards. Submissions trigger a Power Automate flow that calls the Azure Function registration endpoint, which either activates the form automatically (no PHI) or places it in a pending-review queue (PHI).

> **Why a Microsoft Form?** Clinicians already know how to use Forms, no new tool adoption is needed, and Power Automate can trigger directly on submissions. See [Decisions Log — D-011](decisions.md#d-011) for alternatives considered.

---

## Questions to Create

Open [Microsoft Forms](https://forms.office.com) and create a new form with the three questions below. Match the question text, type, and settings exactly.

| # | Question Text | Type | Required | Notes |
|---|---------------|------|----------|-------|
| 1 | Paste your form's share link (open your form in Microsoft Forms, click **Share**, and copy the link) | Text (short answer) | Yes | See validation guidance below |
| 2 | Give your form a short name (e.g., Patient Intake Survey) | Text (short answer) | Yes | Used as the display name for the data pipeline and dashboard |
| 3 | Does this form collect any patient information? (names, dates of birth, medical record numbers, or other data that could identify a patient) | Choice: **Yes** / **No** | Yes | Determines whether the form requires IT approval before activation |

### Question 1 — Link Validation

Microsoft Forms does not support regex validation natively, but you can add a **restriction** to help catch obvious errors:

1. Click the question, then click the **…** menu → **Restrictions**.
2. Choose **URL** as the restriction type if available, otherwise leave as plain text.
3. In the subtitle / helper text, add: *"The link should start with `https://forms.office.com/` or `https://forms.microsoft.com/`."*

The Azure Function performs server-side validation and will reject malformed links with a clear error returned to the Power Automate flow.

> ⚠️ **Important:** The Azure Function extracts fields from the raw response **by position** (1st field = form URL, 2nd = description, 3rd = patient info). Do not reorder the questions in the form — the registration will fail if the order changes.

---

## Form Settings

Configure the form with the following settings:

| Setting | Value |
|---------|-------|
| **Title** | Register Your Form for Analytics |
| **Description** | Use this form to connect your Microsoft Form to the analytics dashboard. It takes about 1 minute. |
| **Who can fill it out** | Only people in my organization |
| **Accept responses** | On |
| **Customize thank you message** | See below |

### Thank You Message

In the form settings, enable **Customize thank you message** and paste:

> Thank you! Your form has been submitted for registration. If it doesn't collect patient info, it will be set up automatically. If it does, your organization's IT team will review it within 1–2 business days.

### Additional Settings

- **Record name** — Enabled (so you can see who submitted each registration).
- **Response receipts** — Optional but recommended so the clinician has a copy.
- **One response per person** — Off (a clinician may register multiple forms).

---

## After Creating the Form

Once the form is saved in Microsoft Forms, complete these steps to connect it to the pipeline.

### Step 1 — Note the Form ID

1. Open the registration form in the Forms editor.
2. Look at the browser URL — it contains an `id=` parameter:
   ```
   https://forms.office.com/Pages/DesignPageV2.aspx?...&id=ePzQbQgk1kOiVUOD-9o_dsPlwRCEj...
   ```
3. Copy the value after `id=` (it's a long base64 string, not a short GUID). This is the form ID you will select in the Power Automate trigger.

### Step 2 — Create the Power Automate Flow

The registration flow is simple — only 4 actions. The Azure Function handles everything else (including auto-creating the data pipeline flow).

```mermaid
flowchart TD
    T[1. Trigger: When a new response is submitted]
    T --> G[2. Get response details]
    G --> H[3. RegisterForm: HTTP POST to /api/register-form]
    H --> C{4. Status code = 200?}
    C -- Yes --> F[5. HTTP POST to Flow API — create data flow]
    C -- No --> ERR[5. Send error email]
    F --> OK[Done]

    classDef primary fill:#4dabf7,stroke:#1864ab,color:#1a1a2e
    classDef success fill:#69db7c,stroke:#2b8a3e,color:#1a1a2e
    classDef warning fill:#ffd43b,stroke:#e67700,color:#1a1a2e
    classDef danger fill:#ff8787,stroke:#c92a2a,color:#1a1a2e
    classDef info fill:#b197fc,stroke:#6741d9,color:#1a1a2e

    T:::primary
    G:::primary
    H:::primary
    C:::warning
    F:::info
    OK:::success
    ERR:::danger
```

**Footnotes — configuration values:**

Run `pwsh scripts/Generate-FlowBody.ps1 -Registration` to get values for footnotes 2–3.

| # | Field | Value |
|---|-------|-------|
| 1 | **Trigger Form** | Select "Register Your Form for Analytics" from the dropdown |
| 2 | **RegisterForm URI** | Copy from script output (e.g., `https://func-forms-dev-ec4zls.azurewebsites.net/api/register-form`) |
| 3 | **x-functions-key** | Copy from script output |
| 4 | **RegisterForm Body** | `{"form_id":"<YOUR-FORM-ID>","raw_response":@{outputs('Get_response_details')?['body']}}` — replace `<YOUR-FORM-ID>` with the registration form's ID from the browser URL `?id=` parameter |
| 5 | **Flow API URL** | `/providers/Microsoft.ProcessSimple/environments/Default-<TENANT-ID>/flows` — replace `<TENANT-ID>` with footnote 8 |
| 6 | **Flow API Body** | `body('RegisterForm')?['flow_create_body']` — enter in the **Expression** tab |
| 7 | **Tenant ID** | Your Entra ID tenant ID (e.g., `6dd0fc78-...`) — find at Azure Portal → Microsoft Entra ID → Overview |

**What the HTTP action returns:**
- Registers the form in the blob storage registry
- Returns `flow_create_body` — a ready-to-use payload for creating the data pipeline flow

Run the helper script to get the HTTP action values:

```powershell
pwsh scripts/Generate-FlowBody.ps1 -Registration
```

Then build the flow:

1. Go to [flow.microsoft.com](https://flow.microsoft.com) → **+ Create** → **Automated cloud flow**
2. Name it: **"Forms to Fabric — Registration Intake"**
3. Trigger: **When a new response is submitted** → select "Register Your Form for Analytics"
4. **+ New step** → **Get response details** → same form, Response Id from trigger
5. **+ New step** → **HTTP POST** to register-form — paste Method, URI, Headers from the script output. **Rename this action to `RegisterForm`** (click `...` → Rename — no hyphens or spaces). Body:

```
{
  "form_id": "<YOUR-FORM-ID>",
  "raw_response": @{outputs('Get_response_details')?['body']}
}
```

> ⚠️ **Important:** The HTTP action MUST be renamed to `RegisterForm` (no hyphens, no spaces). The expression in step 6 references it by this exact name.

6. **+ New step** → **Condition** → `Status code` of RegisterForm ≠ `200`
   - **If no** (success): Add **Invoke an HTTP request** using the **HTTP with Microsoft Entra ID** connector:

     On first use, PA will prompt you to create a connection:

     | Connection prompt | Value |
     |---|---|
     | **Connection Name** | `Flow API` (any name) |
     | **Auth Type** | Leave as default |
     | **MS Entra ID Resource URI (Application ID URI)** | `https://service.flow.microsoft.com` |
     | **Base Resource URL** | `https://api.flow.microsoft.com` |

     Then configure the action:

     | Action field | Value |
     |---|---|
     | **Method** | `POST` |
     | **URL of the request** | `/providers/Microsoft.ProcessSimple/environments/Default-<TENANT-ID>/flows` (see footnote 5) |
     | **Body** | See footnote 6 |

     > No app registration needed — this connector uses your signed-in identity.

   - **If yes** (error): Add **Send an email V2** to notify admin
7. **Save** and enable

> **Note:** The flow creation step runs inside the success branch of the condition. If registration fails, no flow is created. If you skip the flow creation step entirely, the form is still registered — clinicians can create the flow manually using `Generate-FlowBody.ps1`.

### Step 3 — Test End-to-End

1. Open the registration form and submit a test entry with a known form link, a description, and **No** for patient info
2. Verify the Power Automate flow runs successfully (check **Flow run history**)
3. Verify a new flow appears in Power Automate: **"Forms to Fabric — {form name}"**
4. Submit a response to the registered form and check that data appears in Fabric Lakehouse

---

## What Happens After Submission

```mermaid
flowchart TD
    A[Clinician submits registration form] --> B[Power Automate triggers]
    B --> C[Get response details]
    C --> D[HTTP POST /api/register-form]
    D --> E[Form registered in blob storage]
    E --> F[Azure Function calls Flow API]
    F --> G[Data pipeline flow auto-created]
    G --> H{Collects patient info?}
    H -- No --> I[All fields in raw + curated]
    H -- Yes --> J[All fields in raw, unclassified excluded from curated]
    J --> K[IT classifies PHI fields later]
    K --> I

    classDef primary fill:#4dabf7,stroke:#1864ab,color:#1a1a2e
    classDef success fill:#69db7c,stroke:#2b8a3e,color:#1a1a2e
    classDef warning fill:#ffd43b,stroke:#e67700,color:#1a1a2e
    classDef danger fill:#ff8787,stroke:#c92a2a,color:#1a1a2e
    classDef info fill:#b197fc,stroke:#6741d9,color:#1a1a2e
    classDef neutral fill:#ced4da,stroke:#495057,color:#1a1a2e

    A:::primary
    B:::primary
    C:::primary
    D:::primary
    E:::info
    F:::success
    G:::success
    H:::warning
    I:::success
    J:::warning
    K:::info
```

### Flow Details

| Step | Actor | What Happens |
|------|-------|--------------|
| 1 | Clinician | Fills out the registration form with their form link, description, and PHI flag |
| 2 | Power Automate | Triggers automatically on new submission; calls the Azure Function |
| 3 | Azure Function | Validates the link, extracts the form ID, creates a registry entry |
| 4a | System (no PHI) | Sets status to `active`; the form's responses will start flowing into the pipeline |
| 4b | System (PHI) | Sets status to `pending_review`; sends a notification email to the IT team |
| 5 | IT Admin | Reviews the form, classifies PHI fields, and activates via `POST /api/activate-form` |
| 6 | System | Once activated, responses flow into the raw (restricted) layer; PHI fields are excluded from the curated (de-identified) layer |

> **Note:** If a registered form's structure changes later, the Schema Monitor function detects the change, notifies IT, and quarantines new fields in the raw layer only until reviewed. See [Architecture — Schema Monitor](architecture.md) and [Decisions Log — D-014](decisions.md#d-014).

---

## Related Documents

- [Architecture](architecture.md) — Full system design
- [Setup Guide](setup-guide.md) — Azure Function and Power Automate deployment
- [Admin Guide](admin-guide.md) — Managing the form registry
- [Clinician Guide](clinician-guide.md) — End-user instructions
- [Decisions Log](decisions.md) — Why we chose this approach
