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
| 3 | Deploy Azure infrastructure | `azd up` | ~15 min |
| 4 | Create Power Automate flow | Import template | ~10 min |
| 5 | Register and test a form | CLI or self-service | ~10 min |
| 6 | Configure Power BI | Connect to Lakehouse | ~10 min |

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

**Resources created:**

| Resource | Purpose |
|---|---|
| Function App | Processes form responses (Python, Consumption plan) |
| Storage Account | Backing store for the Function App |
| Application Insights | Monitoring and diagnostics |
| Key Vault | Secrets management |
| Managed Identity | Authenticates to Fabric and Key Vault |

**After deployment, grant the Function App access to Fabric:**

1. Open the Fabric portal → your workspace → Settings → Manage access
2. Add the Function App name (it appears as an enterprise application)
3. Assign the **Contributor** role

**Capture the Function App URL and key:**

```powershell
# Function App URL is shown in azd output

# Get the function key
az functionapp keys list `
  --name <function-app-name> `
  --resource-group <resource-group> `
  --query "functionKeys.default" -o tsv
```

Save both — you need them for the Power Automate flow.

---

## Step 4: Create the Power Automate Flow

This flow triggers when someone submits a Microsoft Form response and sends it to the Azure Function for processing.

1. Go to [flow.microsoft.com](https://flow.microsoft.com) → **+ Create** → **Automated cloud flow**
2. Trigger: **When a new response is submitted** (Microsoft Forms) → select your form
3. Action: **Get response details** → same form, Response Id from trigger
4. Action: **HTTP POST** to your Function App:

| Field | Value |
|---|---|
| Method | `POST` |
| URI | `https://<function-app>.azurewebsites.net/api/process-response?code=<function-key>` |
| Headers | `Content-Type: application/json` |
| Body | See template in `power-automate/flow-template.json` |

5. Add a **Condition** → if HTTP status ≠ 200 → send error email to admin
6. Save and enable

> **Tip:** For production, use `power-automate/flow-template-keyvault.json` which reads the function key from Key Vault at runtime — zero-downtime key rotation.

---

## Step 5: Register and Test a Form

**Option A: Self-service** (if Step 6 is set up)
- Fill out the registration form with your form's URL

**Option B: CLI**

```powershell
# Register the form
python scripts/manage_registry.py add-form --form-url "https://forms.office.com/..."

# Add field classifications (for PHI forms)
python scripts/manage_registry.py add-field --form-id "<id>" --question-id "q1" --field-name "patient_name" --contains-phi --deid-method "redact"

# Validate
python scripts/manage_registry.py validate

# Deploy updated config
azd deploy
```

**Test end-to-end:**

1. Submit a test response via your Microsoft Form
2. Check Power Automate → flow run history → should show Succeeded
3. Check Application Insights → Transaction search for `process_response`
4. Check Fabric Lakehouse → Tables → verify raw and curated data appear
5. Verify PHI fields are de-identified in the curated layer

---

## Step 6: Configure Power BI (Optional)

1. Open Power BI → Get data → Microsoft Fabric → Lakehouses
2. Select your workspace and Lakehouse
3. Choose **DirectLake** mode
4. Build visuals: response counts, trends, answer breakdowns
5. Publish to your Fabric workspace

---

## Step 7: Set Up Self-Service Registration (Optional)

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
