<#
.SYNOPSIS
    Lists all Power Automate connections in the current environment.

.DESCRIPTION
    Queries the PowerApps API to discover connection instance names
    for the current service account. Useful for finding the correct
    connection names to pass to Create-RegistrationFlow.ps1.

.PARAMETER EnvironmentId
    Power Platform environment ID. If not provided, uses the default
    environment for the current tenant.

.PARAMETER ApiFilter
    Optional filter to show only connections for a specific API
    (e.g., "office365", "webcontents", "microsoftforms").

.EXAMPLE
    pwsh scripts/List-Connections.ps1
    # Lists all connections

.EXAMPLE
    pwsh scripts/List-Connections.ps1 -ApiFilter "office365"
    # Lists only Office 365 Outlook connections
#>

param(
    [string]$EnvironmentId,
    [string]$ApiFilter
)

Write-Host "`n========================================"
Write-Host "  Power Automate - Connection Discovery"
Write-Host "========================================`n"

# Detect environment
if (-not $EnvironmentId) {
    $tenantId = (az account show --query tenantId -o tsv 2>$null)
    if (-not $tenantId) {
        Write-Host "  ERROR: Not logged into Azure CLI." -ForegroundColor Red
        Write-Host "  For the service account (no Azure subscription), run:" -ForegroundColor Yellow
        Write-Host "    az login --allow-no-subscriptions`n" -ForegroundColor Yellow
        exit 1
    }
    $EnvironmentId = "Default-$tenantId"
}

$currentUser = az account show --query user.name -o tsv 2>$null
Write-Host "  Signed in as: $currentUser"
Write-Host "  Environment:  $EnvironmentId`n"

# Get token for PowerApps API
$token = az account get-access-token --resource "https://service.powerapps.com/" --query accessToken -o tsv 2>$null
if (-not $token) {
    Write-Host "  ERROR: Failed to get PowerApps token." -ForegroundColor Red
    exit 1
}

$headers = @{ Authorization = "Bearer $token" }
$uri = "https://api.powerapps.com/providers/Microsoft.PowerApps/connections?api-version=2020-06-01&`$filter=environment eq '$EnvironmentId'"

try {
    $response = Invoke-RestMethod -Uri $uri -Headers $headers -ErrorAction Stop
} catch {
    Write-Host "  ERROR: Failed to query connections: $($_.Exception.Message)" -ForegroundColor Red
    exit 1
}

$connections = $response.value

if ($ApiFilter) {
    $connections = $connections | Where-Object { $_.properties.apiId -like "*$ApiFilter*" }
}

if (-not $connections -or $connections.Count -eq 0) {
    Write-Host "  No connections found." -ForegroundColor Yellow
    if ($ApiFilter) {
        Write-Host "  (Filtered by: $ApiFilter)" -ForegroundColor Yellow
    }
    exit 0
}

Write-Host "  Found $($connections.Count) connection(s):`n"

$table = $connections | ForEach-Object {
    $status = if ($_.properties.statuses) { $_.properties.statuses[0].status } else { "Unknown" }
    $color = if ($status -eq "Connected") { "Green" } else { "Yellow" }
    [PSCustomObject]@{
        API           = $_.properties.apiId.Split('/')[-1]
        ConnectionName = $_.name
        Status        = $status
        Created       = ([DateTime]$_.properties.createdTime).ToString("yyyy-MM-dd HH:mm")
    }
}

$table | Format-Table -AutoSize

# Show usage hint for registration flow
Write-Host "────────────────────────────────────────"
Write-Host "  Usage with Create-RegistrationFlow.ps1:"
Write-Host "────────────────────────────────────────`n"

$forms = $connections | Where-Object { $_.properties.apiId -like "*microsoftforms*" -and $_.properties.statuses[0].status -eq "Connected" } | Select-Object -First 1
$web   = $connections | Where-Object { $_.properties.apiId -like "*webcontents*"     -and $_.properties.statuses[0].status -eq "Connected" } | Select-Object -First 1
$outlook = $connections | Where-Object { $_.properties.apiId -like "*office365*"     -and $_.properties.statuses[0].status -eq "Connected" } | Select-Object -First 1

$cmd = "pwsh scripts/Create-RegistrationFlow.ps1 ``"
if ($web)     { $cmd += "`n  -WebContentsConnectionName `"$($web.name)`" ``" }
  else        { Write-Host "  WARNING: No connected 'Web Contents' (HTTP with Entra ID) connection found!" -ForegroundColor Yellow }
if ($forms)   { $cmd += "`n  -FormsConnectionName `"$($forms.name)`" ``" }
  else        { Write-Host "  WARNING: No connected 'Microsoft Forms' connection found!" -ForegroundColor Yellow }
if ($outlook) { $cmd += "`n  -OutlookConnectionName `"$($outlook.name)`"" }
  else        { Write-Host "  WARNING: No connected 'Office 365 Outlook' connection found!" -ForegroundColor Yellow }

Write-Host $cmd -ForegroundColor Cyan
Write-Host ""
