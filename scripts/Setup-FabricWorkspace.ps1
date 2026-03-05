<#
.SYNOPSIS
    Sets up the Fabric workspace and Lakehouse via REST API.
.DESCRIPTION
    Creates (or finds) a Fabric workspace and Lakehouse, optionally assigns a
    capacity, and grants the Function App managed identity Contributor access.

    Prerequisites:
    - Azure CLI (az) must be authenticated (az login or OIDC in GitHub Actions)
    - User must have Fabric workspace-creation permissions
    - Fabric capacity must already be provisioned if using -CapacityId
.PARAMETER WorkspaceName
    Name of the Fabric workspace to create or find.
.PARAMETER LakehouseName
    Name of the Lakehouse to create or find.
.PARAMETER CapacityId
    Optional Fabric capacity resource ID (from Bicep output). When provided the
    workspace is assigned to this capacity.
.EXAMPLE
    pwsh scripts/Setup-FabricWorkspace.ps1
.EXAMPLE
    pwsh scripts/Setup-FabricWorkspace.ps1 -CapacityId "/subscriptions/.../Microsoft.Fabric/capacities/my-cap"
#>

param(
    [string]$WorkspaceName  = "Forms to Fabric Analytics",
    [string]$LakehouseName  = "forms_lakehouse",
    [string]$CapacityId     = ""
)

$ErrorActionPreference = "Stop"

# ── Helper ────────────────────────────────────────────────────────────────────

function Get-FabricToken {
    $token = (az account get-access-token --resource "https://api.fabric.microsoft.com" --query "accessToken" -o tsv 2>$null)
    if (-not $token) {
        throw "Failed to get Fabric API token. Run 'az login' first."
    }
    return $token
}

# ── Authenticate ──────────────────────────────────────────────────────────────

Write-Host "`n=== Forms to Fabric — Workspace Setup ===" -ForegroundColor Cyan
Write-Host "Authenticating with Azure CLI..." -ForegroundColor Cyan

$token   = Get-FabricToken
$headers = @{
    "Authorization" = "Bearer $token"
    "Content-Type"  = "application/json"
}
$baseUrl = "https://api.fabric.microsoft.com/v1"

Write-Host "  Authenticated successfully." -ForegroundColor Green

# ── Step 1: Find or Create Workspace ──────────────────────────────────────────

Write-Host "`nStep 1: Workspace" -ForegroundColor Cyan
Write-Host "  Looking for workspace: $WorkspaceName" -ForegroundColor White

$workspaceId = $null

try {
    $workspaces = Invoke-RestMethod -Uri "$baseUrl/workspaces" -Method GET -Headers $headers
    $ws = $workspaces.value | Where-Object { $_.displayName -eq $WorkspaceName }
    if ($ws) {
        $workspaceId = $ws.id
        Write-Host "  Found existing workspace: $workspaceId" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Warning: Could not list workspaces: $($_.Exception.Message)" -ForegroundColor Yellow
}

if (-not $workspaceId) {
    Write-Host "  Creating workspace: $WorkspaceName" -ForegroundColor White
    $wsBody = @{
        displayName = $WorkspaceName
        description = "Forms to Fabric analytics — automated clinical-forms data pipeline"
    } | ConvertTo-Json

    try {
        $ws = Invoke-RestMethod -Uri "$baseUrl/workspaces" -Method POST -Headers $headers -Body $wsBody
        $workspaceId = $ws.id
        Write-Host "  Created workspace: $workspaceId" -ForegroundColor Green
    } catch {
        if ($_.Exception.Response.StatusCode -eq 409) {
            # Race condition — workspace was created between list and create
            $workspaces = Invoke-RestMethod -Uri "$baseUrl/workspaces" -Method GET -Headers $headers
            $ws = $workspaces.value | Where-Object { $_.displayName -eq $WorkspaceName }
            $workspaceId = $ws.id
            Write-Host "  Workspace already exists: $workspaceId" -ForegroundColor Yellow
        } else {
            throw
        }
    }
}

if (-not $workspaceId) {
    throw "Could not find or create workspace '$WorkspaceName'."
}

# ── Step 2: Assign Capacity ──────────────────────────────────────────────────

if ($CapacityId) {
    Write-Host "`nStep 2: Assigning capacity to workspace..." -ForegroundColor Cyan
    $capBody = @{ capacityId = $CapacityId } | ConvertTo-Json
    try {
        Invoke-RestMethod -Uri "$baseUrl/workspaces/$workspaceId/assignToCapacity" `
            -Method POST -Headers $headers -Body $capBody | Out-Null
        Write-Host "  Capacity assigned." -ForegroundColor Green
    } catch {
        Write-Host "  Capacity already assigned or not applicable: $($_.Exception.Message)" -ForegroundColor Yellow
    }
} else {
    Write-Host "`nStep 2: Skipping capacity assignment (no -CapacityId provided)." -ForegroundColor Yellow
}

# ── Step 3: Find or Create Lakehouse ─────────────────────────────────────────

Write-Host "`nStep 3: Lakehouse" -ForegroundColor Cyan
Write-Host "  Looking for lakehouse: $LakehouseName" -ForegroundColor White

$lakehouseId = $null

try {
    $items = Invoke-RestMethod -Uri "$baseUrl/workspaces/$workspaceId/items?type=Lakehouse" `
        -Method GET -Headers $headers
    $lh = $items.value | Where-Object { $_.displayName -eq $LakehouseName }
    if ($lh) {
        $lakehouseId = $lh.id
        Write-Host "  Found existing lakehouse: $lakehouseId" -ForegroundColor Yellow
    }
} catch {
    Write-Host "  Warning: Could not list lakehouses: $($_.Exception.Message)" -ForegroundColor Yellow
}

if (-not $lakehouseId) {
    Write-Host "  Creating lakehouse: $LakehouseName" -ForegroundColor White
    $lhBody = @{
        displayName = $LakehouseName
        type        = "Lakehouse"
    } | ConvertTo-Json

    try {
        $lh = Invoke-RestMethod -Uri "$baseUrl/workspaces/$workspaceId/items" `
            -Method POST -Headers $headers -Body $lhBody
        $lakehouseId = $lh.id
        Write-Host "  Created lakehouse: $lakehouseId" -ForegroundColor Green
    } catch {
        if ($_.Exception.Response.StatusCode -eq 409) {
            $items = Invoke-RestMethod -Uri "$baseUrl/workspaces/$workspaceId/items?type=Lakehouse" `
                -Method GET -Headers $headers
            $lh = $items.value | Where-Object { $_.displayName -eq $LakehouseName }
            $lakehouseId = $lh.id
            Write-Host "  Lakehouse already exists: $lakehouseId" -ForegroundColor Yellow
        } else {
            throw
        }
    }
}

if (-not $lakehouseId) {
    throw "Could not find or create lakehouse '$LakehouseName'."
}

# ── Step 4: Grant Function App Managed Identity Access ───────────────────────

$principalId = $env:FUNCTION_APP_PRINCIPAL_ID

if ($principalId) {
    Write-Host "`nStep 4: Granting Function App managed identity Contributor access..." -ForegroundColor Cyan
    $roleBody = @{
        identifier = $principalId
        groupUserAccessRight = "Contributor"
        principalType = "ServicePrincipal"
    } | ConvertTo-Json

    try {
        Invoke-RestMethod -Uri "$baseUrl/workspaces/$workspaceId/roleAssignments" `
            -Method POST -Headers $headers -Body $roleBody | Out-Null
        Write-Host "  Contributor access granted to principal: $principalId" -ForegroundColor Green
    } catch {
        if ($_.Exception.Response.StatusCode -eq 409) {
            Write-Host "  Role assignment already exists." -ForegroundColor Yellow
        } else {
            Write-Host "  Warning: Could not assign role: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "  You may need to grant Contributor access manually in the Fabric portal." -ForegroundColor Yellow
        }
    }
} else {
    Write-Host "`nStep 4: Skipping role assignment (FUNCTION_APP_PRINCIPAL_ID not set)." -ForegroundColor Yellow
    Write-Host "  To automate this, set the env var before running:" -ForegroundColor White
    Write-Host '  $env:FUNCTION_APP_PRINCIPAL_ID = "<principal-id>"' -ForegroundColor White
}

# ── Summary ──────────────────────────────────────────────────────────────────

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "Setup complete!" -ForegroundColor Green
Write-Host "  Workspace: $workspaceId" -ForegroundColor White
Write-Host "  Lakehouse: $lakehouseId" -ForegroundColor White
Write-Host "========================================" -ForegroundColor Green

Write-Host "`nNext steps:" -ForegroundColor Yellow
Write-Host "  1. Set these in your azd environment:" -ForegroundColor White
Write-Host "     azd env set FABRIC_WORKSPACE_ID $workspaceId" -ForegroundColor White
Write-Host "     azd env set FABRIC_LAKEHOUSE_ID $lakehouseId" -ForegroundColor White
Write-Host "  2. Redeploy: azd deploy" -ForegroundColor White
