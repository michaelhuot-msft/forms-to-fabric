<#
.SYNOPSIS
    Destroy all Forms to Fabric resources: Azure RG, PA flows, Fabric workspace, and registry.
.DESCRIPTION
    Complete teardown script that removes every resource created by the pipeline:
      1. All Power Automate data-pipeline flows (Forms to Fabric - *)
      2. The registration PA flow (Forms to Fabric - Registration Intake)
      3. Fabric workspace and all Lakehouse data
      4. Azure resource group (Function App, Storage, Key Vault, App Insights, Fabric Capacity)
      5. azd environment configuration

    Requires confirmation at each major step. Use -Force to skip confirmations.

    Prerequisites:
      - Azure CLI authenticated (az login)
      - Azure Developer CLI installed (azd) - optional, for env cleanup
      - PowerShell 7+ (pwsh)
.PARAMETER ResourceGroup
    Azure resource group name to delete.
.PARAMETER EnvironmentId
    Power Platform environment ID for PA flow cleanup.
.PARAMETER FabricWorkspaceId
    Fabric workspace ID to delete. If not provided, reads from azd env or ONELAKE_WORKSPACE.
.PARAMETER AzdEnvironment
    azd environment name to clean up (e.g., dev).
.PARAMETER Force
    Skip all confirmations (use for CI/automation only).
.PARAMETER SkipAzure
    Skip Azure resource group deletion.
.PARAMETER SkipFlows
    Skip Power Automate flow deletion.
.PARAMETER SkipFabric
    Skip Fabric workspace deletion.
.EXAMPLE
    pwsh scripts/Destroy-Environment.ps1 -ResourceGroup "rg-forms-to-fabric-dev"
.EXAMPLE
    pwsh scripts/Destroy-Environment.ps1 -ResourceGroup "rg-forms-to-fabric-dev" -Force
.EXAMPLE
    pwsh scripts/Destroy-Environment.ps1 -SkipAzure  # Only clean up PA flows and Fabric
#>

param(
    [string]$ResourceGroup     = "rg-forms-to-fabric-dev",
    [string]$EnvironmentId     = "Default-6dd0fc78-2408-43d6-a255-4383fbda3f76",
    [string]$FabricWorkspaceId = "",
    [string]$FabricCapacityName = "",
    [string]$AzdEnvironment    = "dev",
    [switch]$Force,
    [switch]$SkipAzure,
    [switch]$SkipFlows,
    [switch]$SkipFabric,
    [switch]$Help
)

$ErrorActionPreference = "Stop"

if ($Help) {
    Get-Help $MyInvocation.MyCommand.Path -Detailed
    exit 0
}

# ── Banner ───────────────────────────────────────────────────────────────────

Write-Host ""
Write-Host "============================================" -ForegroundColor Red
Write-Host "  DESTROY ALL FORMS TO FABRIC RESOURCES"     -ForegroundColor Red
Write-Host "============================================" -ForegroundColor Red
Write-Host ""
Write-Host "This will permanently delete:" -ForegroundColor Yellow
if (-not $SkipFlows)  { Write-Host "  - All Power Automate 'Forms to Fabric' flows" -ForegroundColor Yellow }
if (-not $SkipFabric) { Write-Host "  - Fabric workspace and all Lakehouse data" -ForegroundColor Yellow }
if (-not $SkipAzure)  { Write-Host "  - Azure resource group: $ResourceGroup" -ForegroundColor Yellow
                        Write-Host "    (Function App, Storage, Key Vault, App Insights, Fabric Capacity)" -ForegroundColor Yellow }
Write-Host "  - azd environment: $AzdEnvironment" -ForegroundColor Yellow
Write-Host ""

if (-not $Force) {
    $confirm = Read-Host "Type 'DESTROY' to continue (or anything else to cancel)"
    if ($confirm -ne 'DESTROY') {
        Write-Host "Cancelled." -ForegroundColor Green
        exit 0
    }
    Write-Host ""
}

$results = @()

# ── Step 1: Delete Power Automate flows ──────────────────────────────────────

if (-not $SkipFlows) {
    Write-Host "Step 1: Deleting Power Automate flows..." -ForegroundColor Cyan
    try {
        $token = az account get-access-token --resource "https://service.flow.microsoft.com" --query "accessToken" -o tsv 2>$null
        if (-not $token) {
            Write-Host "  Could not get Flow API token. Skipping flow cleanup." -ForegroundColor Yellow
            Write-Host "  You may need to delete flows manually in Power Automate." -ForegroundColor Yellow
            $results += @{ Step = "PA Flows"; Status = "SKIPPED"; Detail = "No token" }
        } else {
            $flowHeaders = @{ "Authorization" = "Bearer $token"; "Accept" = "application/json" }
            $flowsResp = Invoke-RestMethod `
                -Uri "https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/$EnvironmentId/flows" `
                -Headers $flowHeaders -Method GET

            # Find all "Forms to Fabric" flows
            $f2fFlows = $flowsResp.value | Where-Object {
                $_.properties.displayName -like "Forms to Fabric*"
            }

            if ($f2fFlows.Count -eq 0) {
                Write-Host "  No 'Forms to Fabric' flows found." -ForegroundColor Gray
                $results += @{ Step = "PA Flows"; Status = "OK"; Detail = "None found" }
            } else {
                Write-Host "  Found $($f2fFlows.Count) flow(s) to delete:" -ForegroundColor White
                $deleted = 0
                $failed = 0
                foreach ($flow in $f2fFlows) {
                    $name = $flow.properties.displayName
                    $flowId = $flow.name
                    Write-Host "    Deleting: $name..." -NoNewline
                    try {
                        Invoke-RestMethod `
                            -Uri "https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/$EnvironmentId/flows/$flowId" `
                            -Headers $flowHeaders -Method DELETE | Out-Null
                        Write-Host " OK" -ForegroundColor Green
                        $deleted++
                    } catch {
                        Write-Host " FAILED: $($_.Exception.Message)" -ForegroundColor Red
                        $failed++
                    }
                }
                $results += @{ Step = "PA Flows"; Status = "OK"; Detail = "Deleted $deleted, failed $failed" }
            }
        }
    } catch {
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
        $results += @{ Step = "PA Flows"; Status = "FAILED"; Detail = $_.Exception.Message }
    }
    Write-Host ""
} else {
    Write-Host "Step 1: Skipping PA flow cleanup (--SkipFlows)" -ForegroundColor Gray
    Write-Host ""
}

# ── Step 2: Delete Fabric workspace ──────────────────────────────────────────

if (-not $SkipFabric) {
    Write-Host "Step 2: Deleting Fabric workspace..." -ForegroundColor Cyan

    # Try to discover workspace ID from multiple sources
    if (-not $FabricWorkspaceId) {
        try { $FabricWorkspaceId = azd env get-value FABRIC_WORKSPACE_ID 2>$null } catch {}
    }
    if (-not $FabricWorkspaceId) {
        try { $FabricWorkspaceId = azd env get-value ONELAKE_WORKSPACE 2>$null } catch {}
    }
    if (-not $FabricWorkspaceId) {
        $FabricWorkspaceId = $env:FABRIC_WORKSPACE_ID
    }
    if (-not $FabricWorkspaceId) {
        $FabricWorkspaceId = $env:ONELAKE_WORKSPACE
    }
    # Last resort: search by display name via the Fabric API
    if (-not $FabricWorkspaceId) {
        try {
            $fabricToken = az account get-access-token --resource "https://api.fabric.microsoft.com" --query "accessToken" -o tsv 2>$null
            if ($fabricToken) {
                $fabricHeaders = @{ "Authorization" = "Bearer $fabricToken"; "Content-Type" = "application/json" }
                $wsResp = Invoke-RestMethod -Uri "https://api.fabric.microsoft.com/v1/workspaces" -Headers $fabricHeaders -Method GET
                $ws = $wsResp.value | Where-Object { $_.displayName -eq "Forms to Fabric Analytics" }
                if ($ws) {
                    $FabricWorkspaceId = $ws.id
                    Write-Host "  Auto-discovered workspace: $($ws.displayName) ($FabricWorkspaceId)" -ForegroundColor Green
                }
            }
        } catch {}
    }

    if (-not $FabricWorkspaceId) {
        Write-Host "  No workspace ID found. Skipping Fabric cleanup." -ForegroundColor Yellow
        Write-Host "  Provide -FabricWorkspaceId or set FABRIC_WORKSPACE_ID env var." -ForegroundColor Yellow
        $results += @{ Step = "Fabric Workspace"; Status = "SKIPPED"; Detail = "No workspace ID" }
    } else {
        Write-Host "  Workspace ID: $FabricWorkspaceId" -ForegroundColor Gray

        # Resume Fabric capacity if suspended (required before workspace deletion)
        $capacityResumed = $false
        if (-not $FabricCapacityName) {
            try {
                $rgResources = az resource list --resource-group $ResourceGroup --resource-type "Microsoft.Fabric/capacities" --query "[0].name" -o tsv 2>$null
                if ($rgResources) { $FabricCapacityName = $rgResources }
            } catch {}
        }
        if ($FabricCapacityName) {
            try {
                $subId = az account show --query "id" -o tsv 2>$null
                $capUrl = "https://management.azure.com/subscriptions/$subId/resourceGroups/$ResourceGroup/providers/Microsoft.Fabric/capacities/$FabricCapacityName"
                $capState = az rest --method get --url "$capUrl`?api-version=2023-11-01" --query "properties.state" -o tsv 2>$null
                if ($capState -and $capState -ne "Active") {
                    Write-Host "  Resuming Fabric capacity (was $capState) for workspace deletion..." -ForegroundColor Gray
                    az rest --method post --url "$capUrl/resume?api-version=2023-11-01" 2>$null | Out-Null
                    Start-Sleep -Seconds 10
                    $capacityResumed = $true
                    Write-Host "  Capacity resumed." -ForegroundColor Gray
                }
            } catch {
                Write-Host "  Could not resume capacity: $($_.Exception.Message)" -ForegroundColor Yellow
            }
        }

        try {
            $fabricToken = az account get-access-token --resource "https://api.fabric.microsoft.com" --query "accessToken" -o tsv 2>$null
            if ($fabricToken) {
                $fabricHeaders = @{ "Authorization" = "Bearer $fabricToken"; "Content-Type" = "application/json" }
                Invoke-RestMethod `
                    -Uri "https://api.fabric.microsoft.com/v1/workspaces/$FabricWorkspaceId" `
                    -Headers $fabricHeaders -Method DELETE | Out-Null
                Write-Host "  Deleted Fabric workspace." -ForegroundColor Green
                $results += @{ Step = "Fabric Workspace"; Status = "OK"; Detail = "Deleted $FabricWorkspaceId" }
            } else {
                Write-Host "  Could not get Fabric API token." -ForegroundColor Yellow
                $results += @{ Step = "Fabric Workspace"; Status = "SKIPPED"; Detail = "No token" }
            }
        } catch {
            $errMsg = $_.Exception.Message
            if ($errMsg -like "*404*" -or $errMsg -like "*NotFound*") {
                Write-Host "  Workspace already deleted or not found." -ForegroundColor Gray
                $results += @{ Step = "Fabric Workspace"; Status = "OK"; Detail = "Already gone" }
            } elseif ($errMsg -like "*400*" -or $errMsg -like "*Bad Request*") {
                Write-Host "  Workspace deletion returned 400 (capacity may still be starting)." -ForegroundColor Yellow
                Write-Host "  Delete it manually: Fabric Portal > Workspace Settings > Remove this workspace" -ForegroundColor Yellow
                $results += @{ Step = "Fabric Workspace"; Status = "FAILED"; Detail = "400 Bad Request - delete manually from Fabric Portal" }
            } else {
                Write-Host "  Error: $errMsg" -ForegroundColor Red
                $results += @{ Step = "Fabric Workspace"; Status = "FAILED"; Detail = $errMsg }
            }
        }
    }
    Write-Host ""
} else {
    Write-Host "Step 2: Skipping Fabric workspace cleanup (--SkipFabric)" -ForegroundColor Gray
    Write-Host ""
}

# ── Step 3: Delete Azure resource group ──────────────────────────────────────

if (-not $SkipAzure) {
    Write-Host "Step 3: Deleting Azure resource group: $ResourceGroup..." -ForegroundColor Cyan

    # Show what's in the RG before deleting
    try {
        $resources = az resource list --resource-group $ResourceGroup --query "[].{name:name, type:type}" -o json 2>$null | ConvertFrom-Json
        if ($resources -and $resources.Count -gt 0) {
            Write-Host "  Resources to be deleted:" -ForegroundColor White
            foreach ($r in $resources) {
                $shortType = ($r.type -split '/')[-1]
                Write-Host "    - $($r.name) ($shortType)" -ForegroundColor Gray
            }
        }
    } catch {}

    if (-not $Force) {
        $confirm2 = Read-Host "  Delete resource group '$ResourceGroup' and ALL contents? (y/N)"
        if ($confirm2 -ne 'y' -and $confirm2 -ne 'Y') {
            Write-Host "  Skipped resource group deletion." -ForegroundColor Yellow
            $results += @{ Step = "Azure RG"; Status = "SKIPPED"; Detail = "User cancelled" }
        } else {
            try {
                az group delete --name $ResourceGroup --yes --no-wait 2>&1 | Out-Null
                Write-Host "  Resource group deletion initiated (async)." -ForegroundColor Green
                Write-Host "  This may take several minutes to complete in the background." -ForegroundColor Gray
                $results += @{ Step = "Azure RG"; Status = "OK"; Detail = "Deletion initiated (async)" }
            } catch {
                Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
                $results += @{ Step = "Azure RG"; Status = "FAILED"; Detail = $_.Exception.Message }
            }
        }
    } else {
        try {
            az group delete --name $ResourceGroup --yes --no-wait 2>&1 | Out-Null
            Write-Host "  Resource group deletion initiated (async)." -ForegroundColor Green
            $results += @{ Step = "Azure RG"; Status = "OK"; Detail = "Deletion initiated (async)" }
        } catch {
            Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Red
            $results += @{ Step = "Azure RG"; Status = "FAILED"; Detail = $_.Exception.Message }
        }
    }
    Write-Host ""
} else {
    Write-Host "Step 3: Skipping Azure resource group deletion (--SkipAzure)" -ForegroundColor Gray
    Write-Host ""
}

# ── Step 4: Clean up azd environment ─────────────────────────────────────────

Write-Host "Step 4: Cleaning up azd environment..." -ForegroundColor Cyan
try {
    $azdCheck = Get-Command azd -ErrorAction SilentlyContinue
    if ($azdCheck) {
        # Clear azd env values but don't delete the env (user might want to recreate)
        $envValues = @(
            "ONELAKE_WORKSPACE", "ONELAKE_LAKEHOUSE", "FABRIC_CAPACITY_ID",
            "FABRIC_WORKSPACE_ID", "FABRIC_LAKEHOUSE_ID",
            "FUNCTION_APP_PRINCIPAL_ID", "FABRIC_CAPACITY_NAME"
        )
        foreach ($key in $envValues) {
            azd env set $key "" 2>$null
        }
        Write-Host "  Cleared azd environment values." -ForegroundColor Green
        $results += @{ Step = "azd Environment"; Status = "OK"; Detail = "Values cleared" }
    } else {
        Write-Host "  azd not found. Skipping." -ForegroundColor Gray
        $results += @{ Step = "azd Environment"; Status = "SKIPPED"; Detail = "azd not installed" }
    }
} catch {
    Write-Host "  Warning: $($_.Exception.Message)" -ForegroundColor Yellow
    $results += @{ Step = "azd Environment"; Status = "SKIPPED"; Detail = $_.Exception.Message }
}
Write-Host ""

# ── Summary ──────────────────────────────────────────────────────────────────

Write-Host "============================================" -ForegroundColor Cyan
Write-Host "  TEARDOWN SUMMARY"                          -ForegroundColor Cyan
Write-Host "============================================" -ForegroundColor Cyan
Write-Host ""

foreach ($r in $results) {
    $color = switch ($r.Status) {
        "OK"      { "Green" }
        "SKIPPED" { "Yellow" }
        "FAILED"  { "Red" }
        default   { "White" }
    }
    $icon = switch ($r.Status) {
        "OK"      { "OK" }
        "SKIPPED" { "SKIP" }
        "FAILED"  { "FAIL" }
        default   { "??" }
    }
    Write-Host "  $icon  $($r.Step): $($r.Detail)" -ForegroundColor $color
}

Write-Host ""
if (-not $SkipAzure) {
    Write-Host "Note: Resource group deletion runs asynchronously." -ForegroundColor Gray
    Write-Host "Check status: az group show -n $ResourceGroup --query properties.provisioningState -o tsv" -ForegroundColor Gray
    Write-Host ""
}
Write-Host "To recreate everything from scratch:" -ForegroundColor Cyan
Write-Host "  pwsh scripts/Setup-Environment.ps1" -ForegroundColor White
Write-Host "  azd up" -ForegroundColor White
Write-Host ""
