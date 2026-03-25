<#
.SYNOPSIS
    Post-deployment: grants Function App access to Fabric and stores the function key in Key Vault.
.DESCRIPTION
    Run this after 'azd up' to complete the setup. It:
    1. Reads Function App name and principal ID from the deployment outputs
    2. Grants the Function App Contributor access to the Fabric workspace
    3. Retrieves the function key and stores it in Key Vault
    4. Prints the Function App URL for Power Automate configuration
.PARAMETER ResourceGroup
    Resource group name (default: rg-forms-to-fabric-dev)
.PARAMETER EnvironmentName
    azd environment name (default: dev)
.EXAMPLE
    pwsh scripts/Post-Deploy.ps1
#>

param(
    [string]$ResourceGroup  = "",
    [string]$EnvironmentName = ""
)

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Forms to Fabric — Post-Deploy Setup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# ── Auto-detect from azd env ─────────────────────────────────────────────────

if (-not $EnvironmentName) {
    $EnvironmentName = (azd env get-value AZURE_ENV_NAME 2>$null)
    if (-not $EnvironmentName) { $EnvironmentName = "dev" }
}
if (-not $ResourceGroup) {
    $ResourceGroup = (azd env get-value AZURE_RESOURCE_GROUP 2>$null)
}
if (-not $ResourceGroup) {
    $ResourceGroup = "rg-forms-to-fabric-$EnvironmentName"
}

Write-Host "Environment:    $EnvironmentName" -ForegroundColor White
Write-Host "Resource Group: $ResourceGroup" -ForegroundColor White

# ── Step 1: Get Function App details from deployment ─────────────────────────

Write-Host "`nStep 1: Reading deployment outputs..." -ForegroundColor Cyan

$funcAppName = az deployment group show `
    --resource-group $ResourceGroup `
    --name $EnvironmentName `
    --query "properties.outputs.functionAppName.value" -o tsv 2>$null

if (-not $funcAppName) {
    # Try listing function apps in the RG
    $funcAppName = az functionapp list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null
}

if (-not $funcAppName) {
    throw "Could not find Function App in resource group '$ResourceGroup'. Run 'azd up' first."
}

$funcAppUrl = az functionapp show --name $funcAppName --resource-group $ResourceGroup --query "defaultHostName" -o tsv
$principalId = az functionapp identity show --name $funcAppName --resource-group $ResourceGroup --query "principalId" -o tsv

Write-Host "  Function App:  $funcAppName" -ForegroundColor Green
Write-Host "  URL:           https://$funcAppUrl" -ForegroundColor Green
Write-Host "  Principal ID:  $principalId" -ForegroundColor Green

# ── Step 2: Grant Function App access to Fabric workspace ───────────────────

Write-Host "`nStep 2: Granting Function App access to Fabric workspace..." -ForegroundColor Cyan

$workspaceId = $null
try {
    $workspaceId = azd env get-value FABRIC_WORKSPACE_ID 2>$null
    if ($LASTEXITCODE -ne 0) { $workspaceId = $null }
} catch { $workspaceId = $null }
if (-not $workspaceId) {
    $workspaceId = $env:FABRIC_WORKSPACE_ID
}
if (-not $workspaceId) {
    Write-Host "  FABRIC_WORKSPACE_ID not set — skipping." -ForegroundColor Yellow
    Write-Host "  Run Setup-Environment.ps1 first, then re-run this script." -ForegroundColor Yellow
} else {
    $token = az account get-access-token --resource "https://api.fabric.microsoft.com" --query "accessToken" -o tsv
    $headers = @{
        "Authorization" = "Bearer $token"
        "Content-Type"  = "application/json"
    }
    $baseUrl = "https://api.fabric.microsoft.com/v1"

    $roleBody = @{
        principal = @{
            id   = $principalId
            type = "ServicePrincipal"
        }
        role = "Contributor"
    } | ConvertTo-Json -Depth 3

    try {
        Invoke-RestMethod -Uri "$baseUrl/workspaces/$workspaceId/roleAssignments" `
            -Method POST -Headers $headers -Body $roleBody | Out-Null
        Write-Host "  Contributor access granted." -ForegroundColor Green
    } catch {
        $statusCode = $null
        try { $statusCode = $_.Exception.Response.StatusCode.value__ } catch {}
        if ($statusCode -in @(400, 409)) {
            Write-Host "  Role assignment already exists." -ForegroundColor Yellow
        } else {
            Write-Host "  Warning: Could not assign role (HTTP $statusCode): $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "  You may need to grant access manually in the Fabric portal." -ForegroundColor Yellow
        }
    }
}

# ── Step 3: Get function key and store in Key Vault ──────────────────────────

Write-Host "`nStep 3: Retrieving function key and storing in Key Vault..." -ForegroundColor Cyan

$functionKey = az functionapp keys list `
    --name $funcAppName `
    --resource-group $ResourceGroup `
    --query "functionKeys.default" -o tsv 2>$null

if (-not $functionKey) {
    Write-Host "  Warning: Could not retrieve function key." -ForegroundColor Yellow
    Write-Host "  The Function App may still be starting up. Wait a minute and retry." -ForegroundColor Yellow
} else {
    Write-Host "  Function key retrieved." -ForegroundColor Green

    # Store in Key Vault
    $kvName = az deployment group show `
        --resource-group $ResourceGroup `
        --name $EnvironmentName `
        --query "properties.outputs.keyVaultName.value" -o tsv 2>$null

    if (-not $kvName) {
        $kvName = az keyvault list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null
    }

    if ($kvName) {
        az keyvault secret set --vault-name $kvName --name "function-app-key" --value $functionKey --output none 2>$null
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  Function key stored in Key Vault '$kvName' as 'function-app-key'." -ForegroundColor Green
        } else {
            # Try granting the current user access policy and retry
            Write-Host "  Access denied — adding access policy for current user..." -ForegroundColor Yellow
            $currentUpn = az account show --query "user.name" -o tsv 2>$null
            if ($currentUpn) {
                az keyvault set-policy --name $kvName --upn $currentUpn --secret-permissions get set list --output none 2>$null
                if ($LASTEXITCODE -eq 0) {
                    az keyvault secret set --vault-name $kvName --name "function-app-key" --value $functionKey --output none 2>$null
                    if ($LASTEXITCODE -eq 0) {
                        Write-Host "  Function key stored in Key Vault '$kvName' as 'function-app-key'." -ForegroundColor Green
                    } else {
                        Write-Host "  Warning: Still could not store key after adding policy." -ForegroundColor Yellow
                        Write-Host "  Grant yourself 'Key Vault Secrets Officer' or add a secrets set access policy." -ForegroundColor Yellow
                    }
                } else {
                    Write-Host "  Warning: Could not add access policy. Grant yourself secrets set permission on '$kvName'." -ForegroundColor Yellow
                }
            } else {
                Write-Host "  Warning: Could not store key in Key Vault. Grant secrets set permission on '$kvName'." -ForegroundColor Yellow
            }
        }
    } else {
        Write-Host "  Warning: Key Vault not found — key not stored." -ForegroundColor Yellow
    }
}

# ── Summary ──────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Deployment Complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Resources deployed:" -ForegroundColor White
Write-Host "    Function App:      https://$funcAppUrl" -ForegroundColor White
if ($kvName) {
    Write-Host "    Key Vault:         $kvName" -ForegroundColor White
}
if ($workspaceId) {
    Write-Host "    Fabric Workspace:  $workspaceId" -ForegroundColor White
}
Write-Host "    Resource Group:    $ResourceGroup" -ForegroundColor White
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor Yellow
Write-Host "    1. Create the registration Microsoft Form" -ForegroundColor White
Write-Host "       See: docs/registration-form-template.md" -ForegroundColor DarkGray
Write-Host "    2. Create the registration Power Automate flow" -ForegroundColor White
Write-Host "       Run: pwsh scripts/Create-RegistrationFlow.ps1" -ForegroundColor DarkGray
Write-Host "    3. Test by submitting a registration and verifying data in Fabric" -ForegroundColor White
Write-Host "       See: docs/setup-guide.md (Step 4.3)" -ForegroundColor DarkGray
Write-Host ""
