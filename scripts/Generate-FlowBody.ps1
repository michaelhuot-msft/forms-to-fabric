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
    [string]$FunctionKey = ""
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

# ── Resolve Function App URL ─────────────────────────────────────────────────

if (-not $FunctionAppUrl) {
    try { $FunctionAppUrl = azd env get-value FUNCTION_APP_URL 2>$null } catch {}
    if (-not $FunctionAppUrl) {
        try {
            $rg = "rg-forms-to-fabric-dev"
            $funcName = az functionapp list --resource-group $rg --query "[0].defaultHostName" -o tsv 2>$null
            if ($funcName) { $FunctionAppUrl = "https://$funcName" }
        } catch {}
    }
    if (-not $FunctionAppUrl) {
        $FunctionAppUrl = Read-Host "Enter your Function App URL (e.g., https://func-forms-dev-abc123.azurewebsites.net)"
    }
}

if (-not $FunctionKey) {
    $FunctionKey = "<your-function-key>"
}

# ── Generate the body ────────────────────────────────────────────────────────

# Power Automate's "Get response details" returns each answer with an ID
# Power Automate's "Get response details" returns.

Write-Host "`nThe 'Get response details' action returns each answer with an ID like r1, r2, r3, etc." -ForegroundColor White
Write-Host "How many questions does your form have?" -ForegroundColor Cyan

$questionCount = Read-Host "Number of questions"
$questionCount = [int]$questionCount

Write-Host ""

# Build answers array
$answers = @()
for ($i = 1; $i -le $questionCount; $i++) {
    $qId = "r$i"
    $qTitle = Read-Host "Question $i title (e.g., 'Patient Name', 'Satisfaction Rating')"
    $answers += @{
        question_id = $qId
        question = $qTitle
        answer = "@{outputs('Get_response_details')?['body/$qId']}"
    }
}

# Build the full body
$body = [ordered]@{
    form_id = $FormId
    response_id = "@{triggerOutputs()?['body/responseId']}"
    submitted_at = "@{utcNow()}"
    respondent_email = "@{outputs('Get_response_details')?['body/responder']}"
    answers = $answers
}

$json = $body | ConvertTo-Json -Depth 5

# ── Output ───────────────────────────────────────────────────────────────────

Write-Host "`n========================================" -ForegroundColor Green
Write-Host "  HTTP Action Configuration" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green

Write-Host "`nMethod: POST" -ForegroundColor White
Write-Host "URI:    $FunctionAppUrl/api/process-response" -ForegroundColor White
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
Write-Host "  2. Set URI = $FunctionAppUrl/api/process-response" -ForegroundColor White
Write-Host "  3. Add header: Content-Type = application/json" -ForegroundColor White
Write-Host "  4. Add header: x-functions-key = $FunctionKey" -ForegroundColor White
Write-Host "  5. Paste the body JSON above into the Body field" -ForegroundColor White
Write-Host "  6. Power Automate will auto-detect the @{...} expressions" -ForegroundColor White
