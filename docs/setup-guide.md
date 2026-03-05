# Forms to Fabric — Setup Guide

> **Audience:** DevOps engineers and IT administrators
> **Time:** ~45 minutes end-to-end

---

## Prerequisites

| Requirement | Details |
|---|---|
| **Azure subscription** | Contributor access |
| **Microsoft 365 account** | Organizational account with Forms access |
| **Microsoft Fabric** | F2+ capacity (existing, or the setup script creates one) |
| **Azure Developer CLI** | v1.5+ — [install](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) |
| **Azure CLI** | Latest — [install](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| **PowerShell 7+** | [install](https://learn.microsoft.com/powershell/scripting/install/installing-powershell) |
| **Python** | 3.10+ |

---

## Overview

| Step | What | How | Time |
|------|------|-----|------|
| 1 | Clone the repo | `git clone` | 1 min |
| 2 | Set up environment + Fabric | `Setup-Environment.ps1` | ~10 min |
| 3 | Deploy Azure infrastructure | `azd up` + `Post-Deploy.ps1` | ~15 min |
| 4 | Connect your first form | Create form → register → PA flow → test | ~15 min |
| 5 | Configure Power BI | Connect to Lakehouse | ~10 min |
| 6 | Set up self-service registration | Optional | ~15 min |

---

## Step 1: Clone the Repository

```bash
git clone <YOUR_REPO_URL> forms-to-fabric
cd forms-to-fabric
```

---

## Step 2: Set Up Environment and Fabric

A single script configures your azd environment, creates the resource group, provisions Fabric capacity (optional), and creates the workspace + Lakehouse.

```powershell
az login
pwsh scripts/Setup-Environment.ps1
```

Subscription ID and admin email are auto-detected from your Azure CLI login.

**Common options:**

```powershell
# Use a different region
pwsh scripts/Setup-Environment.ps1 -Location eastus

# Skip capacity creation (use your org's existing capacity)
pwsh scripts/Setup-Environment.ps1 -SkipCapacity

# Override all defaults
pwsh scripts/Setup-Environment.ps1 -SubscriptionId "<id>" -AdminEmail "you@org.com" -Location eastus
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| `-SubscriptionId` | Auto-detected | Azure subscription ID |
| `-AdminEmail` | Auto-detected | Fabric admin + notification email |
| `-EnvironmentName` | `dev` | azd environment name |
| `-Location` | `canadaeast` | Azure region |
| `-SkipCapacity` | off | Skip Fabric capacity creation |
| `-CapacityName` | `formstofabric{env}` | Capacity name (alphanumeric only) |
| `-FabricSku` | `F2` | Fabric SKU (F2–F64) |

The script outputs the workspace and Lakehouse IDs and sets them in your azd environment automatically.

<details>
<summary><strong>Manual alternative</strong></summary>

If the automated script doesn't work in your environment:

**2a. Configure azd:**

```powershell
azd env new dev
azd env set AZURE_LOCATION canadaeast
azd env set AZURE_SUBSCRIPTION_ID <your-subscription-id>
azd env set ADMIN_EMAIL you@yourdomain.com
```

**2b. Create resource group + Fabric capacity:**

```powershell
az group create --name rg-forms-to-fabric-dev --location canadaeast

$adminEmail = azd env get-value ADMIN_EMAIL
az deployment group create `
  --resource-group rg-forms-to-fabric-dev `
  --template-file infra/modules/fabric-capacity.bicep `
  --parameters capacityName=formstofabricdev skuName=F2 adminMembers="['$adminEmail']"
```

**2c. Create workspace + Lakehouse:**

```powershell
pwsh scripts/Setup-FabricWorkspace.ps1 -CapacityId "<capacity-id>"
azd env set FABRIC_WORKSPACE_ID <workspace-id>
azd env set FABRIC_LAKEHOUSE_ID <lakehouse-id>
```

**2d. Or create workspace manually:**

1. Go to [app.fabric.microsoft.com](https://app.fabric.microsoft.com) → Workspaces → New workspace
2. Create a Lakehouse named `forms_lakehouse`
3. Copy IDs from the browser URL and set them with `azd env set`

</details>

---

## Step 3: Deploy Azure Infrastructure

```powershell
azd up
```

This packages the Python function app, provisions Azure resources via Bicep, and deploys the code.

Then run the post-deploy script to grant Fabric access and store the function key:

```powershell
pwsh scripts/Post-Deploy.ps1
```

This automatically:
- Grants the Function App managed identity **Contributor** access to your Fabric workspace
- Retrieves the function key and stores it in Key Vault
- Prints the Function App URL (needed for the Power Automate flow)

**Resources created by `azd up`:**

| Resource | Purpose |
|---|---|
| Function App | Processes form responses (Python, Consumption plan) |
| Storage Account | Backing store for the Function App |
| Application Insights | Monitoring and diagnostics |
| Key Vault | Secrets management |
| Managed Identity | Authenticates to Fabric and Key Vault |

---

## Step 4: Connect Your First Form

### 4.1 Create or choose a Microsoft Form

If you don't have a form yet, create one at [forms.microsoft.com](https://forms.microsoft.com). Even a simple 2–3 question test form works.

### 4.2 Register the form in the pipeline

```powershell
# Register — just paste the form URL
python scripts/manage_registry.py add-form --form-url "https://forms.office.com/..."

# For forms with patient info, classify PHI fields
python scripts/manage_registry.py add-field --form-id "<id>" --question-id "q1" --field-name "patient_name" --contains-phi --deid-method "redact"

# Validate and deploy
python scripts/manage_registry.py validate
azd deploy
```

Or use self-service registration if Step 6 is set up.

### 4.3 Create the Power Automate flow

This flow triggers on each form submission and sends the response to the Azure Function.

1. Go to [flow.microsoft.com](https://flow.microsoft.com) → **+ Create** → **Automated cloud flow**
2. Name it (e.g., "Forms to Fabric — My Survey")
3. Trigger: **When a new response is submitted** (Microsoft Forms) → select your form
4. **+ New step** → **Get response details** (Microsoft Forms) → same form, set Response Id to the dynamic value `Response Id` from the trigger
5. **+ New step** → **HTTP** — use the helper script to generate the config:

```powershell
pwsh scripts/Generate-FlowBody.ps1 -FormUrl "https://forms.office.com/..."
```

The script asks for your question titles and outputs the complete HTTP action config (URI, headers, body JSON) ready to paste into Power Automate.

| Field | Value |
|---|---|
| Method | `POST` |
| URI | `https://<your-function-app>.azurewebsites.net/api/process-response` |
| Headers | `Content-Type` : `application/json` |
| Headers | `x-functions-key` : `<your-function-key>` |
| Body | Output from `Generate-FlowBody.ps1` (also saved to `power-automate-body.json`) |

6. **+ New step** → **Condition** → `Status code` is not equal to `200`
   - **If yes**: Add **Send an email (V2)** to notify your admin of the error
   - **If no**: Leave empty (success)
7. **Save** and enable the flow

> **Tip:** For production, store the function key in Key Vault and use the Key Vault connector to retrieve it at runtime. See `power-automate/flow-template-keyvault.json`.

### 4.4 Test end-to-end

1. Submit a test response via your Microsoft Form
2. Check Power Automate → flow run history → should show Succeeded
3. Check Application Insights → Transaction search for `process_response`
4. Check Fabric Lakehouse → Tables → verify raw and curated data appear
5. Verify PHI fields are de-identified in the curated layer

---

## Step 5: Configure Power BI (Optional)

1. Open Power BI → Get data → Microsoft Fabric → Lakehouses
2. Select your workspace and Lakehouse
3. Choose **DirectLake** mode
4. Build visuals: response counts, trends, answer breakdowns
5. Publish to your Fabric workspace

---

## Step 6: Set Up Self-Service Registration (Optional)

Lets clinicians register their own forms via a simple 3-question form.

See [Registration Form Template](registration-form-template.md) for setup instructions.

---

## Fallback: Manual Registration

If the scripts or self-service aren't available:

```powershell
python scripts/manage_registry.py add-form --form-url "https://forms.office.com/..."
python scripts/manage_registry.py validate
azd deploy
```

See the [Admin Guide](admin-guide.md) for full CLI documentation.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| 401 Unauthorized | Invalid function key | Check Key Vault secret or regenerate key |
| Data not in Lakehouse | Managed identity lacks access | Grant Function App Contributor on workspace |
| De-id not applied | Missing field config | Check registry: `manage_registry.py validate` |
| Function timeout | Large payload | Increase `functionTimeout` in `host.json` |
| Form not registered | form_id mismatch | Verify form_id: `manage_registry.py list` |

---

## Next Steps

- [Admin Guide](admin-guide.md) — Operations, monitoring, key rotation
- [Architecture](architecture.md) — Design, security, compliance
- [Pilot Program](pilot-program.md) — Planning a pilot rollout
