# Service Account Setup Guide

> **Purpose:** Eliminate single-admin dependency. All Power Automate flows and connections should be owned by a shared service account, not a personal account.

---

## Why a Service Account?

The Forms to Fabric pipeline relies on several Power Automate components that are tied to the user who created them:

| Component | Risk if owner leaves |
|-----------|---------------------|
| Registration PA flow | Flow stops running — trigger disconnects |
| Forms connector connection | Connection expires — all flows using it break |
| Auto-created data flows | Created under the Entra HTTP connector user — orphaned |
| Flow API authentication | Entra ID connector session expires |

A **service account** (e.g., `forms-pipeline@yourdomain.com`) owns all these components. When individual admins leave, nothing breaks.

---

## Step 1: Create the Service Account

### 1.1 Create a shared mailbox or user account

In Microsoft Entra ID (Azure Portal → Microsoft Entra ID → Users):

1. Click **+ New user** → **Create new user**
2. Display name: `Forms to Fabric Pipeline`
3. User principal name: `forms-pipeline@yourdomain.com`
4. Auto-generate or set a strong password
5. Click **Create**

`[Screenshot placeholder: Entra ID new user creation form]`

### 1.2 Create a shared mailbox for alerts

In the Microsoft 365 Admin Center (admin.microsoft.com):

1. Go to **Teams & groups** → **Shared mailboxes** → **+ Add a shared mailbox**
2. Name: `Forms to Fabric Alerts`
3. Email: `forms-fabric-alerts@yourdomain.com`
4. Click **Create**
5. Add the service account and admin users as members so they receive alert emails

A shared mailbox requires no additional license and can receive failure notifications from the pipeline.

`[Screenshot placeholder: Shared mailbox creation in M365 Admin Center]`

### 1.3 Assign licenses

The service account needs:
- **Microsoft 365 license** (for Microsoft Forms and Outlook access)
- **Power Automate Premium** (required for the HTTP with Microsoft Entra ID connector used by the registration flow)

Go to Microsoft Entra ID → Users → `forms-pipeline@yourdomain.com` → **Licenses** → **+ Assignments** → select the appropriate M365 license.

`[Screenshot placeholder: License assignment page]`

### 1.4 Set password to not expire

```powershell
# Connect to Microsoft Graph PowerShell
Connect-MgGraph -Scopes "User.ReadWrite.All"

# Set password policy
Update-MgUser -UserId "forms-pipeline@yourdomain.com" -PasswordPolicies "DisablePasswordExpiration"
```

Or in Entra ID → Users → `forms-pipeline@yourdomain.com` → **Authentication methods** → configure accordingly.

### 1.5 Enable MFA (recommended)

Even for service accounts, enable MFA or use Conditional Access policies to restrict sign-in to trusted locations only.

`[Screenshot placeholder: MFA configuration for service account]`

---

## Step 2: Create Forms Connection Under Service Account

### 2.1 Sign in to Power Automate as the service account

1. Open an incognito/private browser window
2. Go to [flow.microsoft.com](https://flow.microsoft.com)
3. Sign in as `forms-pipeline@yourdomain.com`

### 2.2 Create a Microsoft Forms connection

1. Go to **Data** → **Connections** → **+ New connection**
2. Search for **Microsoft Forms**
3. Click **Create** → sign in with the service account
4. The connection is now owned by the service account

`[Screenshot placeholder: Power Automate Connections page with Forms connection]`

### 2.3 Create an Office 365 Outlook connection

This connection is used to send failure alert emails from auto-created data flows:

1. Go to **Data** → **Connections** → **+ New connection**
2. Search for **Office 365 Outlook**
3. Click **Create** → sign in with the service account
4. Note the connection ID from the URL (e.g., `shared-office365-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)

`[Screenshot placeholder: Office 365 Outlook connection in Power Automate]`

### 2.4 Note the connection names

1. Click on the newly created Forms connection
2. The URL will contain the connection ID, e.g., `shared-microsoftform-xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`
3. Do the same for the Outlook connection
4. Copy both — you'll need them for the environment variables:
   - `FORMS_CONNECTION_NAME` — the Forms connection ID
   - `OUTLOOK_CONNECTION_NAME` — the Outlook connection ID

`[Screenshot placeholder: Connection details showing connection ID in URL]`

---

## Step 3: Create the Registration Flow Under Service Account

```mermaid
flowchart LR
    Service["Service account"] --> FormsConn["Microsoft Forms connection"]
    Service --> OutlookConn["Office 365 Outlook connection"]
    Service --> Registration["Registration flow"]
    Registration --> FlowApi["Flow API call"]
    FlowApi --> DataFlows["Auto-created data flows"]
    DataFlows --> Alerts["Shared alert mailbox"]

    classDef primary fill:#4dabf7,stroke:#1864ab,color:#1a1a2e
    classDef info fill:#b197fc,stroke:#6741d9,color:#1a1a2e
    classDef success fill:#69db7c,stroke:#2b8a3e,color:#1a1a2e

    class Service primary
    class FormsConn,OutlookConn,Registration,FlowApi info
    class DataFlows,Alerts success
```

### 3.1 While signed in as the service account

Follow the instructions in [Registration Form Template](registration-form-template.md) to create the registration PA flow. All steps are the same, but done under the service account's identity.

Key points:
- The trigger connection should use the service account's Forms connection
- The Entra HTTP connector should be signed in as the service account
- Name the flow: **"Forms to Fabric - Registration Intake"**

### 3.2 Share the registration form

The registration Microsoft Form must be accessible to clinicians:
1. Open the registration form as the service account (or the original creator)
2. **Share** → **Only people in my organization can respond**
3. If the form was created by a different user, share editing access with the service account

`[Screenshot placeholder: Forms sharing settings]`

---

## Step 4: Update Environment Variables

Update the Function App with the service account's connection names and alert settings:

```powershell
az functionapp config appsettings set `
  --name <func-app-name> `
  --resource-group <rg-name> `
  --settings "FUNCTION_APP_KEY=<current-function-key>" `
             "ADMIN_EMAIL=forms-pipeline@yourdomain.com" `
             "FORMS_CONNECTION_NAME=shared-microsoftform-<service-account-connection-id>" `
             "OUTLOOK_CONNECTION_NAME=shared-office365-<service-account-connection-id>" `
             "ALERT_EMAIL=forms-fabric-alerts@yourdomain.com"
```

Where:

- `FUNCTION_APP_KEY` is the current host key used in generated per-form flows
- `FORMS_CONNECTION_NAME` and `OUTLOOK_CONNECTION_NAME` come from the Power Automate connection URLs
- `ALERT_EMAIL` points to the shared mailbox or support list that should receive failure alerts

Then redeploy if you also changed code or other deployment assets:

```powershell
pwsh scripts/Redeploy.ps1
```

For app-setting-only changes, a redeploy is usually not required.

---

## Step 5: Transfer Existing Flows (if applicable)

If flows were previously created under a personal account:

### 5.1 Export and re-import

1. In Power Automate (signed in as the old admin), open each flow
2. **Export** → **Package (.zip)**
3. Sign in as the service account
4. **Import** → upload the .zip
5. Re-map connections to the service account's connections
6. Delete the old flow from the personal account

### 5.2 Or recreate from scratch

For the registration flow, it's simpler to recreate using the documented steps. For auto-created data flows, purge and re-register:

```powershell
pwsh scripts/Manage-Registry.ps1 -Purge
# Then re-submit forms through the registration form (now owned by service account)
```

`[Screenshot placeholder: Flow export/import dialog]`

---

## Step 6: Grant Service Account Access

### 6.1 Fabric workspace access

The service account needs Contributor access to the Fabric workspace:

1. Fabric portal → Workspace → Settings → Manage access
2. Add `forms-pipeline@yourdomain.com` as **Contributor**

### 6.2 Azure resource access (optional)

If the service account needs to run admin scripts:

```powershell
az role assignment create `
  --assignee "forms-pipeline@yourdomain.com" `
  --role "Contributor" `
  --scope "/subscriptions/<sub-id>/resourceGroups/<rg-name>"
```

---

## Step 7: Document the Service Account

Add the service account details to your organization's IT documentation:

| Detail | Value |
|--------|-------|
| **Account** | `forms-pipeline@yourdomain.com` |
| **Purpose** | Owns all Forms to Fabric PA flows and connections |
| **Password stored in** | Azure Key Vault or organization's password manager |
| **MFA** | Enabled (or restricted by Conditional Access) |
| **License** | Microsoft 365 E3/E5 (or equivalent) |
| **Owned flows** | Registration Intake + all auto-created data flows |
| **Owned connections** | Microsoft Forms, Office 365 Outlook, HTTP with Entra ID |

---

## Multi-Admin Access

Multiple admins can manage the pipeline without the service account's password:

| Task | How | Service account needed? |
|------|-----|------------------------|
| View flow run history | Power Platform admin center | No |
| Edit flows | Co-owner on the flow (add admins as co-owners) | No |
| Run admin scripts | `az login` with personal account | No |
| Manage registry | `Manage-Registry.ps1` uses Azure CLI | No |
| Validate registration flow | `Validate-RegistrationFlow.ps1` uses Azure CLI | No |
| Create new PA flow connections | Sign in as service account | Yes |
| Modify registration flow trigger | Sign in as service account | Yes |

### Adding co-owners to flows

So other admins can edit flows without the service account password:

1. Sign in to Power Automate as the service account
2. Open the registration flow → **Share** → add admin users as **Co-owners**
3. Co-owners can edit, enable/disable, and view run history

`[Screenshot placeholder: Flow sharing/co-owner dialog]`

---

## Checklist

- [ ] Service account created in Entra ID
- [ ] Shared mailbox created (`forms-fabric-alerts@yourdomain.com`)
- [ ] M365 license assigned
- [ ] Password set to not expire
- [ ] MFA configured
- [ ] Forms connection created under service account
- [ ] Outlook connection created under service account
- [ ] Registration flow created/transferred to service account
- [ ] `FORMS_CONNECTION_NAME` updated in Function App
- [ ] `OUTLOOK_CONNECTION_NAME` updated in Function App
- [ ] `ALERT_EMAIL` updated in Function App
- [ ] Redeployed (`pwsh scripts/Redeploy.ps1`)
- [ ] Existing flows transferred or re-created
- [ ] Service account has Fabric workspace access
- [ ] Service account details documented
- [ ] Admin co-owners added to flows
- [ ] Original personal-account flows deleted
