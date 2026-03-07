<#
.SYNOPSIS
    Generates a ready-to-paste Power Automate HTTP body for a Microsoft Form.
.DESCRIPTION
    Reads the form's questions from the Microsoft Graph API and produces
    a JSON body you can paste directly into the Power Automate HTTP action.
    No manual question ID mapping needed.
.PARAMETER FormUrl
    The Microsoft Forms URL (paste the link from your browser)
.PARAMETER FormId
    The form ID (alternative to FormUrl if you already have it)
.PARAMETER FunctionAppUrl
    Your Azure Function App URL (from azd output or Post-Deploy.ps1)
.PARAMETER FunctionKey
    Your function key (optional — defaults to placeholder)
.EXAMPLE
    pwsh scripts/Generate-FlowBody.ps1 -FormUrl "https://forms.office.com/Pages/DesignPageV2.aspx?id=ePzQbQgk..."
.EXAMPLE
    pwsh scripts/Generate-FlowBody.ps1 -FormUrl "https://forms.office.com/..." -FunctionAppUrl "https://func-forms-dev-abc123.azurewebsites.net"
#>

param(
    [string]$FormUrl = "",
    [string]$FormId = "",
    [string]$FunctionAppUrl = "",
    [string]$FunctionKey = "",
    [switch]$Registration
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== Generate Power Automate HTTP Body ===" -ForegroundColor Cyan

# ── Resolve Form ID ──────────────────────────────────────────────────────────

if (-not $FormId -and -not $FormUrl) {
    $FormUrl = Read-Host "Paste your Microsoft Forms URL"
}

if (-not $FormId) {
    # Extract id= parameter from URL using regex (no System.Web dependency)
    if ($FormUrl -match "[?&]id=([^&]+)") {
        $FormId = $Matches[1]
    }
    elseif ($FormUrl -match "/r/([A-Za-z0-9_-]+)") {
        $FormId = $Matches[1]
    }

    if (-not $FormId) {
        Write-Host "ERROR: Could not extract form ID from URL." -ForegroundColor Red
        Write-Host "Expected: https://forms.office.com/Pages/DesignPageV2.aspx?...&id=<FORM_ID>" -ForegroundColor Yellow
        exit 1
    }
}

Write-Host "Form ID: $FormId" -ForegroundColor Green

# ── Resolve Function App URL and Key ──────────────────────────────────────────

if (-not $FunctionAppUrl -or -not $FunctionKey) {
    # Try to find the Function App from the resource group
    $rg = "rg-forms-to-fabric-dev"
    $funcAppName = $null

    try {
        $funcAppName = az functionapp list --resource-group $rg --query "[0].name" -o tsv 2>$null
    } catch {}

    if ($funcAppName) {
        if (-not $FunctionAppUrl) {
            $hostName = az functionapp show --name $funcAppName --resource-group $rg --query "defaultHostName" -o tsv 2>$null
            if ($hostName) {
                $FunctionAppUrl = "https://$hostName"
                Write-Host "Function App: $FunctionAppUrl" -ForegroundColor Green
            }
        }
        if (-not $FunctionKey) {
            $FunctionKey = az functionapp keys list --name $funcAppName --resource-group $rg --query "functionKeys.default" -o tsv 2>$null
            if ($FunctionKey) {
                Write-Host "Function Key: (retrieved)" -ForegroundColor Green
            }
        }
    }
}

if (-not $FunctionAppUrl) {
    $FunctionAppUrl = Read-Host "Enter your Function App URL (e.g., https://func-forms-dev-abc123.azurewebsites.net)"
}
if (-not $FunctionKey) {
    $FunctionKey = Read-Host "Enter your function key (from Azure portal or Key Vault)"
}

# ── Generate the body ────────────────────────────────────────────────────────

if ($Registration) {
    # Registration form — calls /api/register-form
    $endpoint = "$FunctionAppUrl/api/register-form"
} else {
    # Data collection form — calls /api/process-response
    $endpoint = "$FunctionAppUrl/api/process-response"
}

# Both modes use the same raw_response passthrough body
$json = @"
{
  "form_id": "$FormId",
  "raw_response": @{outputs('Get_response_details')?['body']}
}
"@

# ── Output ───────────────────────────────────────────────────────────────────

# Get tenant ID for Flow API config
$tenantId = az account show --query "tenantId" -o tsv 2>$null
if (-not $tenantId) { $tenantId = "<your-tenant-id>" }
$envId = "Default-$tenantId"

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  Registration Flow Configuration" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host "`n── Step 5: RegisterForm (HTTP POST) ──" -ForegroundColor Cyan
Write-Host "  Rename this action to: RegisterForm" -ForegroundColor Yellow
Write-Host "  Method:  POST" -ForegroundColor White
Write-Host "  URI:     $endpoint" -ForegroundColor White
Write-Host "  Headers:" -ForegroundColor White
Write-Host "    Content-Type:    application/json" -ForegroundColor White
Write-Host "    x-functions-key: $FunctionKey" -ForegroundColor White
Write-Host "  Body:" -ForegroundColor White
Write-Host "────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host $json -ForegroundColor White
Write-Host "────────────────────────────────────────" -ForegroundColor DarkGray

Write-Host "`n── Step 6: Condition (Status code = 200?) ──" -ForegroundColor Cyan
Write-Host "  If yes (success) → add HTTP POST below" -ForegroundColor White
Write-Host "  If no (error) → Send error email" -ForegroundColor White

Write-Host "`n── Inside Yes branch: Create Data Flow (HTTP POST) ──" -ForegroundColor Cyan
Write-Host "  Method:  POST" -ForegroundColor White
Write-Host "  URI:     https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/$envId/flows" -ForegroundColor White
Write-Host "  Headers:" -ForegroundColor White
Write-Host "    Content-Type: application/json" -ForegroundColor White
Write-Host "  Body (enter in Expression tab):" -ForegroundColor White
Write-Host "    body('RegisterForm')?['flow_create_body']" -ForegroundColor Yellow
Write-Host "  Authentication:" -ForegroundColor White
Write-Host "    Type:     Active Directory OAuth" -ForegroundColor White
Write-Host "    Authority: https://login.microsoftonline.com" -ForegroundColor White
Write-Host "    Tenant:   $tenantId" -ForegroundColor White
Write-Host "    Audience: https://service.flow.microsoft.com" -ForegroundColor White
Write-Host "    Client ID: (leave blank)" -ForegroundColor White

# Save to file
$outPath = "power-automate-body.json"
$json | Out-File -FilePath $outPath -Encoding utf8
Write-Host "`nBody also saved to: $outPath" -ForegroundColor Green
