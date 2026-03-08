<#
.SYNOPSIS
    One-command setup: creates Fabric capacity, workspace, and Lakehouse,
    then sets all azd environment variables automatically.
.DESCRIPTION
    Combines environment configuration, Fabric capacity provisioning,
    and workspace/lakehouse creation into a single script.

    Prerequisites:
    - Azure CLI authenticated (az login)
    - Azure Developer CLI installed (azd)
    - PowerShell 7+ (pwsh)
.PARAMETER EnvironmentName
    azd environment name (e.g., dev, staging, prod)
.PARAMETER Location
    Azure region (e.g., canadaeast, eastus)
.PARAMETER SubscriptionId
    Azure subscription ID
.PARAMETER AdminEmail
    Admin email (Fabric capacity admin + error notifications)
.PARAMETER SkipCapacity
    Skip Fabric capacity creation (use if your org already has one)
.PARAMETER CapacityName
    Fabric capacity name (alphanumeric only, no hyphens)
.PARAMETER SkipValidation
    Skip the final preflight validation before running azd up
.EXAMPLE
    pwsh scripts/Setup-Environment.ps1 -SubscriptionId "7a5070f6-..." -AdminEmail "you@org.com"
.EXAMPLE
    pwsh scripts/Setup-Environment.ps1
.EXAMPLE
    pwsh scripts/Setup-Environment.ps1 -SkipCapacity
.EXAMPLE
    pwsh scripts/Setup-Environment.ps1 -SubscriptionId "7a5070f6-..." -AdminEmail "you@org.com"
#>

param(
    [string]$EnvironmentName = "dev",
    [string]$Location        = "canadaeast",
    [string]$SubscriptionId  = "",
    [string]$AdminEmail      = "",
    [switch]$SkipCapacity,
    [switch]$SkipValidation,
    [string]$CapacityName    = "",
    [string]$ResourceGroup   = "",
    [string]$FabricSku       = "F2"
)

$ErrorActionPreference = "Stop"
$usingDefaultLocation = -not $PSBoundParameters.ContainsKey("Location")

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Forms to Fabric — Environment Setup" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# ── Auto-detect values from Azure CLI if not provided ────────────────────────

if (-not $SubscriptionId) {
    Write-Host "Detecting subscription ID from Azure CLI..." -ForegroundColor White
    $SubscriptionId = (az account show --query "id" -o tsv 2>$null)
    if (-not $SubscriptionId) {
        throw "Could not detect subscription. Run 'az login' first, or pass -SubscriptionId."
    }
    Write-Host "  Found: $SubscriptionId" -ForegroundColor Green
}

if (-not $AdminEmail) {
    Write-Host "Detecting admin email from Azure CLI..." -ForegroundColor White
    $AdminEmail = (az account show --query "user.name" -o tsv 2>$null)
    if (-not $AdminEmail) {
        $AdminEmail = Read-Host "Could not auto-detect. Enter your admin email"
    }
    Write-Host "  Found: $AdminEmail" -ForegroundColor Green
}

if (-not $CapacityName) { $CapacityName = "formstofabric$EnvironmentName" }
if (-not $ResourceGroup) { $ResourceGroup = "rg-forms-to-fabric-$EnvironmentName" }

Write-Host "Selecting Azure subscription..." -ForegroundColor White
az account set --subscription $SubscriptionId 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Could not select subscription '$SubscriptionId'. Verify access and try again."
}
$subscriptionName = (az account show --query "name" -o tsv 2>$null)
Write-Host "  Using: $subscriptionName ($SubscriptionId)" -ForegroundColor Green

Write-Host "`n────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  Configuration Summary" -ForegroundColor White
Write-Host "────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  Environment:    $EnvironmentName"
Write-Host "  Location:       $Location"
Write-Host "  Subscription:   $subscriptionName ($SubscriptionId)"
Write-Host "  Admin:          $AdminEmail"
Write-Host "  Resource Group: $ResourceGroup"
if (-not $SkipCapacity) {
    Write-Host "  Capacity:       $CapacityName ($FabricSku)"
}
Write-Host "────────────────────────────────────────" -ForegroundColor DarkGray

if ($usingDefaultLocation) {
    Write-Host "  Note: Location '$Location' is the script default." -ForegroundColor Yellow
    Write-Host "  Pass -Location <region> to change it (e.g. -Location eastus)." -ForegroundColor Yellow
}
Write-Host ""

$confirm = Read-Host "Proceed with these settings? (Y/n)"
if ($confirm -and $confirm.Trim().ToLower() -notin @("y", "yes", "")) {
    Write-Host "`nSetup cancelled. Re-run with the correct parameters, for example:" -ForegroundColor Yellow
    Write-Host "  pwsh scripts/Setup-Environment.ps1 -Location eastus -AdminEmail you@org.com" -ForegroundColor White
    Write-Host "`nAvailable parameters:" -ForegroundColor White
    Write-Host "  -EnvironmentName <name>    azd environment (default: dev)" -ForegroundColor White
    Write-Host "  -Location <region>         Azure region (default: canadaeast)" -ForegroundColor White
    Write-Host "  -SubscriptionId <id>       Azure subscription ID" -ForegroundColor White
    Write-Host "  -AdminEmail <email>        Admin email for alerts and capacity" -ForegroundColor White
    Write-Host "  -SkipCapacity              Skip Fabric capacity creation" -ForegroundColor White
    Write-Host "  -CapacityName <name>       Fabric capacity name" -ForegroundColor White
    Write-Host "  -FabricSku <sku>           Fabric SKU (F2-F64)" -ForegroundColor White
    Write-Host "  -ResourceGroup <name>      Azure resource group name" -ForegroundColor White
    exit 0
}

# ── Step 1: azd environment ──────────────────────────────────────────────────

Write-Host "Step 1: Configuring azd environment..." -ForegroundColor Cyan
# Select existing env or create new one
azd env select $EnvironmentName 2>$null
if ($LASTEXITCODE -ne 0) {
    azd env new $EnvironmentName 2>$null
}
azd env set AZURE_LOCATION $Location
azd env set AZURE_SUBSCRIPTION_ID $SubscriptionId
azd env set ADMIN_EMAIL $AdminEmail
azd env set AZURE_ENV_NAME $EnvironmentName
Write-Host "  azd environment '$EnvironmentName' configured." -ForegroundColor Green

# ── Step 2: Resource Group ───────────────────────────────────────────────────

Write-Host "`nStep 2: Creating resource group..." -ForegroundColor Cyan
az group create --name $ResourceGroup --location $Location --output none 2>$null
Write-Host "  Resource group '$ResourceGroup' ready." -ForegroundColor Green

# ── Step 3: Fabric Capacity (optional) ───────────────────────────────────────

$capacityId = ""
if (-not $SkipCapacity) {
    Write-Host "`nStep 3: Provisioning Fabric capacity ($CapacityName, $FabricSku)..." -ForegroundColor Cyan
    $deployOutput = az deployment group create `
        --resource-group $ResourceGroup `
        --template-file infra/modules/fabric-capacity.bicep `
        --parameters capacityName=$CapacityName skuName=$FabricSku adminMembers="['$AdminEmail']" `
        --query "properties.outputs.capacityId.value" -o tsv 2>&1

    if ($LASTEXITCODE -eq 0) {
        $capacityId = $deployOutput
        Write-Host "  Capacity created: $capacityId" -ForegroundColor Green
    } else {
        Write-Host "  Warning: Capacity deployment returned: $deployOutput" -ForegroundColor Yellow
        Write-Host "  Continuing without capacity assignment..." -ForegroundColor Yellow
    }
} else {
    Write-Host "`nStep 3: Skipping capacity creation (-SkipCapacity)." -ForegroundColor Yellow
}

# ── Step 4: Workspace + Lakehouse ────────────────────────────────────────────

Write-Host "`nStep 4: Creating Fabric workspace and Lakehouse..." -ForegroundColor Cyan
$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$setupArgs = @{}
if ($capacityId) { $setupArgs["CapacityId"] = $capacityId }

& "$scriptDir/Setup-FabricWorkspace.ps1" @setupArgs

# Read IDs from the script output by re-querying
$token = (az account get-access-token --resource "https://api.fabric.microsoft.com" --query "accessToken" -o tsv)
$headers = @{ "Authorization" = "Bearer $token"; "Content-Type" = "application/json" }
$baseUrl = "https://api.fabric.microsoft.com/v1"

$workspaces = Invoke-RestMethod -Uri "$baseUrl/workspaces" -Method GET -Headers $headers
$ws = $workspaces.value | Where-Object { $_.displayName -eq "Forms to Fabric Analytics" }
$workspaceId = $ws.id

$items = Invoke-RestMethod -Uri "$baseUrl/workspaces/$workspaceId/items?type=Lakehouse" -Method GET -Headers $headers
$lh = $items.value | Where-Object { $_.displayName -eq "forms_lakehouse" }
$lakehouseId = $lh.id

# ── Step 5: Set Fabric IDs in azd ───────────────────────────────────────────

Write-Host "`nStep 5: Setting Fabric IDs in azd environment..." -ForegroundColor Cyan
azd env set FABRIC_WORKSPACE_ID $workspaceId
azd env set FABRIC_LAKEHOUSE_ID $lakehouseId
Write-Host "  FABRIC_WORKSPACE_ID = $workspaceId" -ForegroundColor Green
Write-Host "  FABRIC_LAKEHOUSE_ID = $lakehouseId" -ForegroundColor Green

# ── Step 6: Validate azd deployment inputs ───────────────────────────────────

if (-not $SkipValidation) {
    Write-Host "`nStep 6: Validating deployment inputs..." -ForegroundColor Cyan
    & "$scriptDir/Validate-Environment.ps1" `
        -EnvironmentName $EnvironmentName `
        -ResourceGroup $ResourceGroup `
        -SubscriptionId $SubscriptionId `
        -Location $Location `
        -FabricWorkspaceId $workspaceId `
        -FabricLakehouseId $lakehouseId
} else {
    Write-Host "`nStep 6: Skipping validation (-SkipValidation)." -ForegroundColor Yellow
}

# ── Done ────────────────────────────────────────────────────────────────────

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Environment setup complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host "`nAll azd variables configured. Run:" -ForegroundColor Yellow
Write-Host "  azd up" -ForegroundColor White
Write-Host "`nThis will deploy the Function App, Key Vault, Storage," -ForegroundColor White
Write-Host "and App Insights, pre-configured to write to your Lakehouse." -ForegroundColor White
