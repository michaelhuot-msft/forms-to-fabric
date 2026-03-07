<#
.SYNOPSIS
    Redeploy the Azure Function code (no infrastructure changes).
.DESCRIPTION
    Pulls latest code, cleans build artifacts, and deploys to Azure
    via remote build. Use after any Python code changes.
.PARAMETER FunctionApp
    Name of the Function App (default: auto-detected from resource group)
.PARAMETER ResourceGroup
    Resource group name (default: rg-forms-to-fabric-dev)
.EXAMPLE
    pwsh scripts/Redeploy.ps1
.EXAMPLE
    pwsh scripts/Redeploy.ps1 -FunctionApp func-forms-dev-abc123
#>

param(
    [string]$FunctionApp = "",
    [string]$ResourceGroup = "rg-forms-to-fabric-dev"
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== Forms to Fabric — Redeploy ===" -ForegroundColor Cyan

# Auto-detect function app name
if (-not $FunctionApp) {
    $FunctionApp = az functionapp list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null
    if (-not $FunctionApp) {
        throw "Could not find Function App in resource group '$ResourceGroup'"
    }
}
Write-Host "Function App: $FunctionApp" -ForegroundColor Green

# Pull latest
Write-Host "`nPulling latest code..." -ForegroundColor Cyan
git pull

# Navigate to functions directory
$functionsDir = Join-Path $PSScriptRoot ".." "src" "functions"
Set-Location $functionsDir

# Clean build artifacts
Write-Host "Cleaning build artifacts..." -ForegroundColor Cyan
Get-ChildItem -Recurse -Directory -Filter "__pycache__" | Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force .python_packages -ErrorAction SilentlyContinue

# Deploy
Write-Host "Deploying via remote build..." -ForegroundColor Cyan
func azure functionapp publish $FunctionApp --python --build remote

Write-Host "`n=== Redeploy complete ===" -ForegroundColor Green
