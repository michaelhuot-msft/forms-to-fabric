# Forms to Fabric - Deployment Prerequisites

> **Audience:** DevOps engineers, IT administrators, and developers setting up the pipeline
>
> **Last audited:** 2026-03-08

---

## Quick Reference

| Category | Count | Details |
|----------|-------|---------|
| CLI tools | 5 required + 1 optional | az, azd, pwsh, python, git, func |
| Python packages | 10 runtime + 4 dev | See [Python Dependencies](#python-dependencies) |
| Bicep modules | 5 | Function App, Storage, Key Vault, App Insights, Fabric Capacity |
| GitHub Actions | 5 | checkout, setup-python, setup-azd, login, gitleaks |
| External APIs | 6 | Azure RM, Fabric, Flow Management, OneLake endpoints |

---

## CLI Tools

### Required

| Tool | Min Version | Install | Used By |
|------|-------------|---------|---------|
| **Azure CLI** (`az`) | 2.50+ | [Install](https://aka.ms/cli) | All scripts, Bicep validation, RBAC, storage |
| **Azure Developer CLI** (`azd`) | 1.5+ | [Install](https://aka.ms/azd) | Infrastructure deployment, environment config |
| **PowerShell** (`pwsh`) | 7.0+ | [Install](https://aka.ms/powershell) | All admin scripts (`.ps1`) |
| **Python** | 3.11.x | [Install](https://python.org) | Azure Functions runtime, tests, linting |
| **Git** | 2.30+ | [Install](https://git-scm.com) | Source control, pre-commit hook |

### Optional

| Tool | Install | Used By |
|------|---------|---------|
| **Azure Functions Core Tools** (`func`) | [Install](https://learn.microsoft.com/azure/azure-functions/functions-run-local) | Local testing, `Redeploy.ps1` |
| **Bicep CLI** | Auto-installed via `az bicep install` | IaC templates (handled by Azure CLI) |

### PowerShell Modules

No extra PowerShell modules are required. The `.ps1` scripts use built-in PowerShell cmdlets plus external CLIs such as `az`, `azd`, `git`, and `func`.

### Verify Installation

```powershell
# Run this to check all tools
az version
azd version
pwsh --version
python --version
git --version
func --version  # optional
```

---

## Python Dependencies

### Runtime Packages (`src/functions/requirements.txt`)

| Package | Version | Purpose |
|---------|---------|---------|
| `azure-functions` | latest | Azure Functions v2 programming model |
| `azure-identity` | latest | Managed identity and DefaultAzureCredential |
| `azure-storage-blob` | latest | Blob storage for form registry |
| `azure-keyvault-secrets` | latest | Key Vault secret access |
| `azure-mgmt-web` | latest | Function App management (key rotation) |
| `pydantic` | >=2.0 | Request/response validation |
| `pyarrow` | latest | Apache Arrow columnar format |
| `deltalake` | latest | Delta Lake table writes to OneLake |
| `httpx` | latest | Async HTTP client |
| `requests` | latest | HTTP client for REST calls |

### Development/CI Packages

| Package | Purpose | Installed By |
|---------|---------|--------------|
| `pytest` | Test framework | CI workflow |
| `pytest-cov` | Code coverage | CI workflow |
| `ruff` | Linting and formatting | CI workflow |
| `jsonschema` | Registry schema validation | CI workflow |

### Install Locally

```powershell
cd src/functions
pip install -r requirements.txt
pip install pytest pytest-cov ruff jsonschema  # dev tools
```

---

## Azure Resources Provisioned

All resources are created via Bicep templates in `infra/`:

| Resource | Bicep Module | SKU/Tier | Purpose |
|----------|-------------|----------|---------|
| **Function App** | `function-app.bicep` | Linux Consumption (Y1) | Python 3.11 runtime |
| **App Service Plan** | `function-app.bicep` | Y1 (Dynamic) | Serverless hosting |
| **Storage Account** | `storage.bicep` | Standard_LRS, StorageV2 | Function state + form registry blob |
| **Key Vault** | `key-vault.bicep` | Standard | Function key storage, soft-delete 90d |
| **Application Insights** | `app-insights.bicep` | Per-GB pricing | Monitoring and diagnostics |
| **Log Analytics Workspace** | `app-insights.bicep` | PerGB2018 | Log aggregation |
| **Fabric Capacity** | `fabric-capacity.bicep` | F2 (configurable) | OneLake storage + compute |

### Bicep API Versions

| Provider | API Version | Notes |
|----------|-------------|-------|
| `Microsoft.Web/serverfarms` | 2023-12-01 | Current |
| `Microsoft.Web/sites` | 2023-12-01 | Current |
| `Microsoft.Storage/storageAccounts` | 2023-05-01 | Current |
| `Microsoft.Fabric/capacities` | 2023-11-01 | Current |
| `Microsoft.KeyVault/vaults` | 2023-07-01 | Current |
| `Microsoft.OperationalInsights/workspaces` | 2023-09-01 | Current |
| `Microsoft.Insights/components` | 2020-02-02 | Older, monitor for updates |
| `Microsoft.Authorization/roleAssignments` | 2022-04-01 | Current |

### RBAC Role Assignments (Managed Identity)

The Function App's system-assigned managed identity receives:

| Role | Role ID | Scope |
|------|---------|-------|
| Storage Blob Data Owner | `b7e6dc6d-...` | Storage Account |
| Storage Account Contributor | `17d1049b-...` | Storage Account |
| Storage Queue Data Contributor | `974c5e8b-...` | Storage Account |

---

## Azure Function App Settings

Set automatically by Bicep and post-deploy scripts:

| Setting | Source | Purpose |
|---------|--------|---------|
| `FUNCTIONS_WORKER_RUNTIME` | Bicep | `python` |
| `FUNCTIONS_EXTENSION_VERSION` | Bicep | `~4` |
| `ENABLE_ORYX_BUILD` | Bicep | `true` — remote pip install |
| `SCM_DO_BUILD_DURING_DEPLOYMENT` | Bicep | `true` — Oryx build |
| `AzureWebJobsStorage__accountName` | Bicep | Managed identity storage auth |
| `APPINSIGHTS_INSTRUMENTATIONKEY` | Bicep | Telemetry |
| `KEY_VAULT_URL` | Bicep | Secret access |
| `ONELAKE_WORKSPACE` | Bicep | Fabric workspace GUID |
| `ONELAKE_LAKEHOUSE` | Bicep | Lakehouse GUID |
| `POWER_PLATFORM_ENVIRONMENT_ID` | azd / Bicep input | PA environment for flow creation |
| `FORMS_CONNECTION_NAME` | Manual | PA Forms connector ID |
| `OUTLOOK_CONNECTION_NAME` | Manual | PA Outlook connector ID (alerts) |
| `FUNCTION_APP_KEY` | Manual | Host key embedded into generated per-form flows |
| `ADMIN_EMAIL` | Manual | Admin notification email |
| `ALERT_EMAIL` | Manual | Failure alert recipient (defaults to ADMIN_EMAIL) |
| `ADMIN_ALERT_EMAIL` | Manual (optional) | Schema monitor logging target |
| `ALLOWED_RAW_ACCESS_GROUP` | Manual (optional) | Expected admin group for RBAC audit |
| `FUNCTION_APP_MANAGED_IDENTITY_ID` | Manual (optional) | Managed identity identifier for RBAC audit filtering |

> `Post-Deploy.ps1` retrieves the current function key and stores it in Key Vault, but it does **not** set `FUNCTION_APP_KEY` for you. If you rely on auto-created per-form flows, keep the `FUNCTION_APP_KEY` app setting in sync with the current host key.

---

## GitHub Environment Configuration

### Repository Environment: `production`

| Variable | Required | Example | Purpose |
|----------|----------|---------|---------|
| `AZURE_CLIENT_ID` | Yes | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` | App registration client ID |
| `AZURE_TENANT_ID` | Yes | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` | Entra ID tenant |
| `AZURE_SUBSCRIPTION_ID` | Yes | `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx` | Target subscription |
| `AZURE_ENV_NAME` | Yes | `dev` | azd environment name |
| `AZURE_LOCATION` | Yes | `eastus` | Azure region |
| `FABRIC_RESOURCE_GROUP` | For capacity mgmt | `rg-forms-to-fabric-dev` | Capacity suspend/resume |
| `FABRIC_CAPACITY_NAME` | For capacity mgmt | `formstofabricdev` | Capacity suspend/resume |
| `FABRIC_CAPACITY_ID` | If existing | Resource ID | Skip capacity creation |
| `FABRIC_WORKSPACE_ID` | Optional | GUID | Workspace provisioning / CI setup |
| `FUNCTION_APP_PRINCIPAL_ID` | Optional | GUID | Fabric RBAC |

### Authentication: OIDC Federated Credentials

No secrets stored in GitHub. Authentication uses a trust relationship:

1. Create Azure AD app registration
2. Add federated credential for the `production` environment
3. Subject: `repo:michaelhuot-msft/forms-to-fabric:environment:production`

> `Setup-Environment.ps1` populates your local `azd` environment. It does **not** sync values into GitHub repository environments; add the GitHub `production` variables separately in repository settings.

---

## GitHub Actions Workflows

### `deploy.yml` — CI/CD Pipeline

| Job | Runner | Tools | Purpose |
|-----|--------|-------|---------|
| test | ubuntu-latest | Python 3.11, pytest | 69 unit tests |
| lint | ubuntu-latest | ruff | Linting + format check |
| bicep | ubuntu-latest | az bicep | IaC validation |
| schema | ubuntu-latest | jsonschema | Registry schema validation |
| secrets | ubuntu-latest | gitleaks | Credential scanning |
| deploy | ubuntu-latest | azd, az, pwsh | Deploy to Azure (main only) |

### `fabric-capacity.yml` — Cost Management

| Trigger | Action | Tools |
|---------|--------|-------|
| Daily 04:00 UTC (10 PM CST) | Suspend capacity | az rest |
| Manual dispatch | Resume / Suspend / Status | az rest |

### GitHub Actions Used

| Action | Version | Purpose |
|--------|---------|---------|
| `actions/checkout` | v4 | Source checkout |
| `actions/setup-python` | v5 | Python 3.11 setup |
| `Azure/setup-azd` | v2 | Azure Developer CLI |
| `azure/login` | v2 | OIDC Azure authentication |
| `gitleaks/gitleaks-action` | v2 | Secret scanning |

---

## External APIs

Scripts and workflows call these APIs (all authenticated via Azure CLI tokens):

| API | Base URL | Used By |
|-----|----------|---------|
| **Azure Resource Manager** | `https://management.azure.com` | Bicep deploy, capacity mgmt, RG operations |
| **Fabric REST API** | `https://api.fabric.microsoft.com` | Workspace/Lakehouse creation, RBAC |
| **Power Automate (auth)** | `https://service.flow.microsoft.com` | Token acquisition for Flow API |
| **Flow Management API** | `https://api.flow.microsoft.com` | Create/list/delete PA flows |
| **OneLake (data plane)** | `https://onelake.dfs.fabric.microsoft.com` | Delta Lake writes (via deltalake library) |
| **OneLake (blob compat)** | `https://onelake.blob.fabric.microsoft.com` | Delta Lake list operations |

---

## Power Platform Requirements

| Component | License Required | Purpose |
|-----------|-----------------|---------|
| Microsoft Forms | M365 E3/E5 or equivalent | Form creation and responses |
| Power Automate | Premium (for HTTP connector) | Flow automation |
| Office 365 Outlook connector | M365 license | Failure alert emails |
| Microsoft Forms connector | M365 license | Form trigger + response details |

### Power Automate Connections Needed

| Connector | Connection Reference | Created By |
|-----------|---------------------|------------|
| Microsoft Forms | `shared_microsoftforms` | Service account |
| Office 365 Outlook | `shared_office365` | Service account |
| HTTP with Microsoft Entra ID | Manual setup | Service account |

---

## Scripts Reference

| Script | Purpose | Required Tools |
|--------|---------|----------------|
| `Setup-Environment.ps1` | One-command environment setup | az, azd, pwsh |
| `Post-Deploy.ps1` | Post-deployment config (RBAC, keys) | az, azd, pwsh |
| `Redeploy.ps1` | Quick code redeploy | git, func, az, pwsh |
| `Setup-FabricWorkspace.ps1` | Create Fabric workspace + Lakehouse | az, pwsh |
| `Manage-Registry.ps1` | List/remove/purge form registry | az, pwsh |
| `Validate-RegistrationFlow.ps1` | Validate PA flow structure | az, pwsh |
| `Generate-FlowBody.ps1` | Generate PA flow HTTP body | az, pwsh |
| `Destroy-Environment.ps1` | Complete teardown | az, azd (optional), pwsh |
| `rotate_function_key.py` | Rotate Function App host key | python, az (auth) |
| `install-hooks.sh` | Install git pre-commit hook | sh/bash |

---

## Pre-Deployment Checklist

```
CLI Tools:
  [ ] Azure CLI (az) installed and logged in
  [ ] Azure Developer CLI (azd) installed
  [ ] PowerShell 7+ (pwsh) installed
  [ ] Python 3.11 installed
  [ ] Git installed
  [ ] Azure Functions Core Tools (func) installed (optional)

Azure:
  [ ] Active Azure subscription with Contributor access
  [ ] Azure AD app registration with federated credential
  [ ] Fabric license available (F2+ capacity)

GitHub:
  [ ] Repository cloned
  [ ] "production" environment created in repo settings
  [ ] Environment variables configured (see table above)

Power Platform:
  [ ] M365 account with Forms + Power Automate access
  [ ] Power Automate Premium license (for HTTP connector)
  [ ] Service account created (see service-account-guide.md)
  [ ] Forms and Outlook connections created under service account
```
