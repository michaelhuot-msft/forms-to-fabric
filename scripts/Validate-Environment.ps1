<#
.SYNOPSIS
    Validates the azd environment and infrastructure template before running azd up.
.DESCRIPTION
    Performs a preflight check against the current azd environment:
    - Confirms the selected subscription and resource group
    - Validates the Azure location value
    - Builds infra/main.bicep
    - Uses what-if to discover the Key Vault name and checks for soft-deleted collisions
    - Runs az deployment group validate with the resolved Fabric IDs

    This script is safe to run multiple times and does not create resources.
.PARAMETER EnvironmentName
    azd environment name. Defaults to AZURE_ENV_NAME from the selected azd environment.
.PARAMETER ResourceGroup
    Azure resource group name. Defaults to rg-forms-to-fabric-<environment>.
.PARAMETER SubscriptionId
    Azure subscription ID. Defaults to AZURE_SUBSCRIPTION_ID from azd env or the current Azure CLI context.
.PARAMETER Location
    Azure region name such as centralus or eastus. Defaults to AZURE_LOCATION from azd env.
.PARAMETER FabricWorkspaceId
    Fabric workspace ID. Defaults to FABRIC_WORKSPACE_ID from azd env.
.PARAMETER FabricLakehouseId
    Fabric Lakehouse ID. Defaults to FABRIC_LAKEHOUSE_ID from azd env.
.EXAMPLE
    pwsh scripts/Validate-Environment.ps1
.EXAMPLE
    pwsh scripts/Validate-Environment.ps1 -EnvironmentName dev -ResourceGroup rg-forms-to-fabric-dev
#>

param(
    [string]$EnvironmentName = "",
    [string]$ResourceGroup = "",
    [string]$SubscriptionId = "",
    [string]$Location = "",
    [string]$FabricWorkspaceId = "",
    [string]$FabricLakehouseId = ""
)

$ErrorActionPreference = "Stop"

function Get-AzdEnvValue {
    param([string]$Name)

    $value = azd env get-value $Name 2>$null
    if ($LASTEXITCODE -ne 0) {
        return ""
    }

    return "$value".Trim()
}

function Get-WhatIfChanges {
    param(
        [string]$ResourceGroupName,
        [string]$EnvName,
        [string]$AzureLocation,
        [string]$WorkspaceId,
        [string]$LakehouseId
    )

    $whatIfOutput = az deployment group what-if `
        --resource-group $ResourceGroupName `
        --template-file infra/main.bicep `
        --parameters environmentName=$EnvName location=$AzureLocation fabricWorkspaceId=$WorkspaceId fabricLakehouseId=$LakehouseId `
        --result-format ResourceIdOnly `
        --no-pretty-print `
        -o json 2>$null

    if ($LASTEXITCODE -ne 0 -or -not $whatIfOutput) {
        return @()
    }

    $parsed = $whatIfOutput | ConvertFrom-Json
    if ($null -ne $parsed.properties -and $null -ne $parsed.properties.changes) {
        return @($parsed.properties.changes)
    }
    if ($null -ne $parsed.changes) {
        return @($parsed.changes)
    }
    if ($parsed -is [System.Array]) {
        return @($parsed)
    }

    return @()
}

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Forms to Fabric - Environment Validation" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

if (-not $EnvironmentName) {
    $EnvironmentName = Get-AzdEnvValue -Name "AZURE_ENV_NAME"
    if (-not $EnvironmentName) { $EnvironmentName = "dev" }
}
if (-not $ResourceGroup) {
    $ResourceGroup = "rg-forms-to-fabric-$EnvironmentName"
}
if (-not $SubscriptionId) {
    $SubscriptionId = Get-AzdEnvValue -Name "AZURE_SUBSCRIPTION_ID"
    if (-not $SubscriptionId) {
        $SubscriptionId = (az account show --query "id" -o tsv 2>$null)
    }
}
if (-not $Location) {
    $Location = Get-AzdEnvValue -Name "AZURE_LOCATION"
}
if (-not $FabricWorkspaceId) {
    $FabricWorkspaceId = Get-AzdEnvValue -Name "FABRIC_WORKSPACE_ID"
}
if (-not $FabricLakehouseId) {
    $FabricLakehouseId = Get-AzdEnvValue -Name "FABRIC_LAKEHOUSE_ID"
}

$missing = @()
if (-not $SubscriptionId) { $missing += "AZURE_SUBSCRIPTION_ID" }
if (-not $Location) { $missing += "AZURE_LOCATION" }
if (-not $FabricWorkspaceId) { $missing += "FABRIC_WORKSPACE_ID" }
if (-not $FabricLakehouseId) { $missing += "FABRIC_LAKEHOUSE_ID" }
if ($missing.Count -gt 0) {
    throw "Missing required values: $($missing -join ', '). Run Setup-Environment.ps1 first or pass them explicitly."
}

Write-Host "Environment:    $EnvironmentName" -ForegroundColor White
Write-Host "Resource Group: $ResourceGroup" -ForegroundColor White
Write-Host "Subscription:   $SubscriptionId" -ForegroundColor White
Write-Host "Location:       $Location" -ForegroundColor White

Write-Host "`nStep 1: Selecting Azure subscription..." -ForegroundColor Cyan
az account set --subscription $SubscriptionId 2>$null
if ($LASTEXITCODE -ne 0) {
    throw "Could not select subscription '$SubscriptionId'."
}
$subscriptionName = az account show --query "name" -o tsv 2>$null
Write-Host "  Using: $subscriptionName" -ForegroundColor Green

Write-Host "`nStep 2: Validating Azure region..." -ForegroundColor Cyan
$resolvedLocation = az account list-locations --query "[?name=='$Location'].displayName | [0]" -o tsv 2>$null
if (-not $resolvedLocation) {
    throw "Location '$Location' is not a valid Azure region name for this subscription."
}
Write-Host "  Region confirmed: $resolvedLocation" -ForegroundColor Green

Write-Host "`nStep 3: Checking resource group..." -ForegroundColor Cyan
$resourceGroupId = az group show --name $ResourceGroup --query "id" -o tsv 2>$null
if (-not $resourceGroupId) {
    throw "Resource group '$ResourceGroup' was not found. Run Setup-Environment.ps1 first."
}
Write-Host "  Resource group exists." -ForegroundColor Green

Write-Host "`nStep 4: Building Bicep template..." -ForegroundColor Cyan
az bicep build --file infra/main.bicep 2>&1 | Out-Null
if ($LASTEXITCODE -ne 0) {
    throw "Bicep build failed for infra/main.bicep."
}
Write-Host "  infra/main.bicep builds successfully." -ForegroundColor Green

Write-Host "`nStep 5: Checking derived Key Vault name..." -ForegroundColor Cyan
$changes = Get-WhatIfChanges `
    -ResourceGroupName $ResourceGroup `
    -EnvName $EnvironmentName `
    -AzureLocation $Location `
    -WorkspaceId $FabricWorkspaceId `
    -LakehouseId $FabricLakehouseId

$keyVaultResourceId = $changes `
    | Where-Object { $_.resourceId -match "/providers/Microsoft.KeyVault/vaults/" } `
    | Select-Object -ExpandProperty resourceId -First 1

if ($keyVaultResourceId) {
    $keyVaultName = ($keyVaultResourceId -split "/")[-1]
    Write-Host "  Planned Key Vault: $keyVaultName" -ForegroundColor Green

    $deletedVaultName = az keyvault list-deleted --query "[?name=='$keyVaultName'].name | [0]" -o tsv 2>$null
    if ($deletedVaultName) {
        Write-Host "  Blocking issue: soft-deleted Key Vault '$deletedVaultName' still exists." -ForegroundColor Red
        Write-Host "  Purge it before running azd up:" -ForegroundColor Yellow
        Write-Host "    az keyvault purge --name $deletedVaultName --location $Location" -ForegroundColor White
        throw "Validation failed because the planned Key Vault name is blocked by soft-delete recovery."
    }
} else {
    Write-Host "  Warning: could not resolve the planned Key Vault name from what-if output." -ForegroundColor Yellow
}

Write-Host "`nStep 6: Validating the ARM deployment..." -ForegroundColor Cyan
$validationOutput = az deployment group validate `
    --resource-group $ResourceGroup `
    --template-file infra/main.bicep `
    --parameters environmentName=$EnvironmentName location=$Location fabricWorkspaceId=$FabricWorkspaceId fabricLakehouseId=$FabricLakehouseId `
    --query "properties.provisioningState" `
    -o tsv 2>&1

if ($LASTEXITCODE -ne 0) {
    $outputText = ($validationOutput | Out-String)
    $vaultMatch = [regex]::Match($outputText, "VaultAlreadyExists: The vault name '([^']+)'")
    if ($vaultMatch.Success) {
        $vaultName = $vaultMatch.Groups[1].Value
        Write-Host "  Blocking issue: Key Vault name '$vaultName' cannot be reused yet." -ForegroundColor Red
        Write-Host "  Purge it before running azd up:" -ForegroundColor Yellow
        Write-Host "    az keyvault purge --name $vaultName --location $Location" -ForegroundColor White
    }

    throw "Deployment validation failed. Resolve the issue above before running azd up."
}

Write-Host "  ARM validation passed." -ForegroundColor Green

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Validation complete - safe to run azd up" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
