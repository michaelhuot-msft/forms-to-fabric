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
    # Registration form — fixed 3 questions, calls /api/register-form
    $endpoint = "$FunctionAppUrl/api/register-form"
    $json = @"
{
  "form_url": "@{outputs('Get_response_details')?['body/r1']}",
  "description": "@{outputs('Get_response_details')?['body/r2']}",
  "has_phi": @{if(equals(outputs('Get_response_details')?['body/r3'], 'Yes'), true, false)}
}
"@
} else {
    # Data collection form — variable questions, calls /api/process-response
    $endpoint = "$FunctionAppUrl/api/process-response"

    Write-Host "`nThe 'Get response details' action returns each answer as r1, r2, r3, etc." -ForegroundColor White
    $questionCount = Read-Host "How many questions does your form have?"
    $questionCount = [int]$questionCount

    $answers = @()
    for ($i = 1; $i -le $questionCount; $i++) {
        $qId = "r$i"
        $qTitle = Read-Host "  Question $i title"
        $answers += @{
            question_id = $qId
            question    = $qTitle
            answer      = "@{outputs('Get_response_details')?['body/$qId']}"
        }
    }

    $body = [ordered]@{
        form_id          = $FormId
        response_id      = "@{triggerOutputs()?['body/responseId']}"
        submitted_at     = "@{utcNow()}"
        respondent_email = "@{outputs('Get_response_details')?['body/responder']}"
        answers          = $answers
    }
    $json = $body | ConvertTo-Json -Depth 5
}

# ── Output ───────────────────────────────────────────────────────────────────

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  HTTP Action Configuration" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host "`nMethod: POST" -ForegroundColor White
Write-Host "URI:    $endpoint" -ForegroundColor White
Write-Host "`nHeaders:" -ForegroundColor White
Write-Host "  Content-Type:    application/json" -ForegroundColor White
Write-Host "  x-functions-key: $FunctionKey" -ForegroundColor White

Write-Host "`nBody (copy and paste into Power Automate):" -ForegroundColor Yellow
Write-Host "────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host $json -ForegroundColor White
Write-Host "────────────────────────────────────────" -ForegroundColor DarkGray

# Also save to file
$outPath = "power-automate-body.json"
$json | Out-File -FilePath $outPath -Encoding utf8
Write-Host "`nAlso saved to: $outPath" -ForegroundColor Green

Write-Host "`nSteps in Power Automate:" -ForegroundColor Yellow
Write-Host "  1. In the HTTP action, set Method = POST" -ForegroundColor White
Write-Host "  2. Set URI = $endpoint" -ForegroundColor White
Write-Host "  3. Add header: Content-Type = application/json" -ForegroundColor White
Write-Host "  4. Add header: x-functions-key = $FunctionKey" -ForegroundColor White
Write-Host "  5. Paste the body JSON above into the Body field" -ForegroundColor White
Write-Host "  6. Power Automate will auto-detect the @{...} expressions" -ForegroundColor White
