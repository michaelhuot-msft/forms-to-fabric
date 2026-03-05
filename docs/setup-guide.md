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
| 4 | Set up self-service registration | Create registration form + PA flow | ~15 min |
| 5 | Connect your first data form | Register via self-service → create PA data flow → test | ~15 min |
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

## Step 4: Set Up Self-Service Registration

Clinicians register their data collection forms by filling out a simple 3-question registration form. This step creates that registration form and connects it to the pipeline.

### 4.1 Create the registration form

Follow [Registration Form Template](registration-form-template.md) to create a "Register Your Form for Analytics" form in Microsoft Forms with 3 questions:
1. Paste your form's share link
2. Briefly describe what this form is for
3. Does this form collect any patient information? (Yes / No)

### 4.2 Create the registration Power Automate flow

Run the helper script to get the HTTP action values:

```powershell
pwsh scripts/Generate-FlowBody.ps1 -Registration
```

Then build the flow:

1. Go to [flow.microsoft.com](https://flow.microsoft.com) → **+ Create** → **Automated cloud flow**
2. Name it: "Forms to Fabric — Registration Intake"
3. Trigger: **When a new response is submitted** → select "Register Your Form for Analytics"
4. **+ New step** → **Get response details** → same form, Response Id from trigger
5. **+ New step** → **HTTP** — paste Method, URI, Headers, and Body from the script output
6. **+ New step** → **Condition** → `Status code` ≠ `200` → send error email
7. Save and enable

### 4.3 Test the registration flow

1. Open the registration form and submit a test entry with a real data form URL
2. Check Power Automate flow run history → should show Succeeded
3. Verify the form appears in the registry: `python scripts/manage_registry.py list`

---

## Step 5: Connect Your First Data Form

### 5.1 Create or choose a data collection form

If you don't have one yet, create a simple test form at [forms.microsoft.com](https://forms.microsoft.com).

### 5.2 Register it via self-service

1. Open the registration form you created in Step 4
2. Paste the data form's share link
3. Add a description
4. Select whether it collects patient info
5. Submit — the form is registered automatically (non-PHI) or queued for IT review (PHI)

### 5.3 Create the data pipeline flow

Run the helper script to get the HTTP action values for the data form:

```powershell
pwsh scripts/Generate-FlowBody.ps1 -FormUrl "https://forms.office.com/..."
```

Then build the flow:

1. **+ Create** → **Automated cloud flow**
2. Name it (e.g., "Forms to Fabric — Patient Survey")
3. Trigger: **When a new response is submitted** → select your data form
4. **+ New step** → **Get response details** → same form, Response Id from trigger
5. **+ New step** → **HTTP** — paste Method, URI, Headers, and Body from the script output
6. **+ New step** → **Condition** → `Status code` ≠ `200` → send error email
7. Save and enable

### 5.4 Test end-to-end

1. Submit a test response via your data form
2. Check Power Automate → flow run history → Succeeded
3. Check Fabric Lakehouse → Tables → verify data appears
4. Verify PHI fields are de-identified in the curated layer

---

## Step 6: Configure Power BI (Optional)

1. Open Power BI → Get data → Microsoft Fabric → Lakehouses
2. Select your workspace and Lakehouse
3. Choose **DirectLake** mode
4. Build visuals: response counts, trends, answer breakdowns
5. Publish to your Fabric workspace

---

## Fallback: Manual Registration (CLI)

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
