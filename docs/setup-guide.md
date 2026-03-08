# Forms to Fabric — Setup Guide

> **Audience:** DevOps engineers and IT administrators
> **Time:** ~45 minutes end-to-end

---

## Prerequisites

For a comprehensive list of all tools, packages, APIs, and configurations, see [Deployment Prerequisites](deployment-prerequisites.md).

| Requirement | Details |
|---|---|
| **Azure subscription** | Contributor access |
| **Microsoft 365 account** | Organizational account with Forms access |
| **Microsoft Fabric** | F2+ capacity (existing, or the setup script creates one) |
| **Azure Developer CLI** | v1.5+ — [install](https://learn.microsoft.com/azure/developer/azure-developer-cli/install-azd) |
| **Azure CLI** | Latest — [install](https://learn.microsoft.com/cli/azure/install-azure-cli) |
| **PowerShell 7+** | [install](https://learn.microsoft.com/powershell/scripting/install/installing-powershell) |
| **Python** | 3.11+ |
| **Power Automate Premium** | Required for auto flow creation. Standard license works for manual import. |

---

## Overview

| Step | What | How | Time |
|------|------|-----|------|
| 1 | Clone the repo | `git clone` | 1 min |
| 2 | Set up environment + Fabric | `Setup-Environment.ps1` | ~10 min |
| 3 | Deploy Azure infrastructure | `azd up` + `Post-Deploy.ps1` | ~15 min |
| 4 | Set up self-service registration | Create registration form + PA flow | ~15 min |
| 5 | Test the pipeline | Submit a test response → verify both flows run → check Lakehouse | ~5 min |
| 6 | Configure Power BI | Connect to Lakehouse | ~10 min |

---

## Step 1: Clone the Repository

```bash
git clone <YOUR_REPO_URL> forms-to-fabric
cd forms-to-fabric
```

Optional but recommended for contributors: install the local pre-commit hook so Bicep is validated before each commit.

```bash
sh scripts/install-hooks.sh
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

**For later code-only updates:** use `pwsh scripts/Redeploy.ps1` to redeploy the Azure Function via remote build without reprovisioning infrastructure. Continue using `azd up` when you change Bicep or other Azure resources.

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

The registration form + flow handles everything: form registration, data pipeline flow creation, and notifications.

### 4.1 Create the registration form

Follow [Registration Form Template](registration-form-template.md) to create a "Register Your Form for Analytics" form with 3 questions:
1. Paste your form's share link
2. Briefly describe what this form is for
3. Does this form collect any patient information? (Yes / No)

### 4.2 Create the registration Power Automate flow

Run the helper script to get the HTTP action values:

```powershell
pwsh scripts/Generate-FlowBody.ps1 -Registration
```

Then build the flow with these steps:

1. **Trigger**: When a new response is submitted → select "Register Your Form for Analytics"
2. **Get response details** → same form, Response Id from trigger
3. **HTTP POST** to `/api/register-form` — paste URI, headers, body from the script output
4. **HTTP GET** to generate the data pipeline flow:
   - URI: `https://<function-app>/api/generate-flow?form_id=@{body('HTTP')?['form_id']}`
   - Headers: `x-functions-key` (same key)
5. **Create Flow** (Power Automate Management connector):
   - Environment: your Power Platform environment ID
   - Display Name: `Forms to Fabric — @{body('HTTP')?['form_name']}`
   - Definition: `@{body('HTTP_2')}` (output from step 4)
6. **Condition** → Status code of step 3 ≠ 200 → send error email
7. **Save** and enable

> ⚠️ **The "Create Flow" action (step 5) requires Power Automate Premium.** If not available, clinicians can manually import the flow definition from the generate-flow endpoint. See [Registration Form Template](registration-form-template.md) for details.

### 4.3 Test the registration flow

1. Submit a test entry via the registration form with a real form URL
2. Check Power Automate flow run history → should show Succeeded
3. Verify TWO things were created:
   - The form appears in the registry: `az storage blob download --account-name <storage> --container-name form-registry --name registry.json --auth-mode key --file -`
   - A new data pipeline flow appears in Power Automate: "Forms to Fabric — {form name}"

---

## Step 5: Test the Pipeline

1. Open your data form and submit a test response
2. Check Power Automate → flow run history for "Forms to Fabric — {form name}" → should show Succeeded
3. Check Fabric Lakehouse → Tables → look for `{table_name}_raw`
4. If the form has PHI fields classified, also check `{table_name}_curated`

> **Note:** Tables are named `{target_table}_raw` and `{target_table}_curated` in Delta Lake format. The `target_table` is auto-derived from the form name during registration.

---

## Step 6: Configure Power BI (Optional)

1. Open Power BI → Get data → Microsoft Fabric → Lakehouses
2. Select your workspace and Lakehouse
3. Choose **DirectLake** mode
4. Build visuals: response counts, trends, answer breakdowns
5. Publish to your Fabric workspace

---

## Fallback: Manual Registration

If the self-service registration form isn't available, use the PowerShell script to list existing forms and manage the registry:

```powershell
pwsh scripts/Manage-Registry.ps1 -List
```

To register a new form manually, use the self-service registration form or call the `POST /api/register-form` endpoint directly. See the [Admin Guide](admin-guide.md) for details.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| 401 Unauthorized | Invalid function key | Check Key Vault secret or regenerate key |
| 404 on function endpoint | Functions not registered | See "Functions not loading" below |
| Data not in Lakehouse | Managed identity lacks access | Grant Function App Contributor on workspace |
| De-id not applied | Missing field config | Edit the blob registry to add field configuration |
| Function timeout | Large payload | Increase `functionTimeout` in `host.json` |
| Form not registered | form_id mismatch | Verify form_id: `pwsh scripts/Manage-Registry.ps1 -List` |
| Storage 403 Forbidden | Subscription blocks shared key access | Add `SecurityControl=Ignore` tag to storage account |
| Local commits miss Bicep validation | Git hook not installed | Run `sh scripts/install-hooks.sh` from the repo root |

### Functions not loading after deployment

If `azd deploy` succeeds but endpoints return 404:

1. **Check Python version matches** — the Function App must run Python 3.11:
   ```powershell
   az functionapp config show --name <func-name> --resource-group <rg> --query "linuxFxVersion"
   # Should show "Python|3.11"
   ```

2. **Verify remote build ran** — check deployment logs for "pip install":
   ```powershell
   az functionapp log deployment show --name <func-name> --resource-group <rg> --query "[-3:].[message]" -o tsv
   # Should show "Deployment successful"
   ```

3. **If remote build fails silently** — your subscription may block shared key access. Add the `SecurityControl=Ignore` tag:
   ```powershell
   az storage account update --name <storage-name> --resource-group <rg> --allow-shared-key-access true --tags SecurityControl=Ignore
   ```

4. **Test directly** — `az functionapp function list` has a delay with v2 Python. Hit the endpoint instead:
   ```powershell
   $key = az functionapp keys list --name <func-name> --resource-group <rg> --query "functionKeys.default" -o tsv
   Invoke-WebRequest -Uri "https://<func-name>.azurewebsites.net/api/process-response?code=$key" -Method POST -Body '{}' -ContentType "application/json"
   # Should return 400 (validation error) — that means it's working
   ```

---

## Next Steps

- [Admin Guide](admin-guide.md) — Operations, monitoring, key rotation
- [Architecture](architecture.md) — Design, security, compliance
- [Pilot Program](pilot-program.md) — Planning a pilot rollout

## Teardown

To remove everything and start fresh:

```powershell
pwsh scripts/Destroy-Environment.ps1 -ResourceGroup "rg-forms-to-fabric-dev"
```

See the [Teardown and Cleanup](admin-guide.md#teardown-and-cleanup) section of the Admin Guide for full details.
