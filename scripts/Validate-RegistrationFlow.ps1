<#
.SYNOPSIS
    Validates the PA Registration Intake flow matches the expected configuration.
.DESCRIPTION
    Checks the deployed Power Automate registration flow for:
    - Correct trigger (Forms webhook)
    - RegisterForm HTTP action exists with correct URI
    - Condition step exists
    - Entra ID HTTP action exists in True branch
    - Error email exists in False branch
.EXAMPLE
    pwsh scripts/Validate-RegistrationFlow.ps1
.EXAMPLE
    pwsh scripts/Validate-RegistrationFlow.ps1 -FlowName "Forms to Fabric - Registration Intake"
#>

param(
    [string]$FlowName = "Forms to Fabric - Registration Intake",
    [string]$EnvironmentId = ""
)

$ErrorActionPreference = "Stop"

Write-Host "`n=== Validate Registration Flow ===" -ForegroundColor Cyan

# Get token
$token = az account get-access-token --resource "https://service.flow.microsoft.com" --query "accessToken" -o tsv 2>$null
if (-not $token) { throw "Run 'az login' first" }
$headers = @{ "Authorization" = "Bearer $token"; "Accept" = "application/json" }

# Get environment
if (-not $EnvironmentId) {
    $envResp = Invoke-RestMethod -Uri "https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments" -Headers $headers
    $EnvironmentId = $envResp.value[0].name
}

# Find the flow
$flowsResp = Invoke-RestMethod -Uri "https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/$EnvironmentId/flows" -Headers $headers
$flow = $flowsResp.value | Where-Object { $_.properties.displayName -eq $FlowName }

if (-not $flow) {
    Write-Host "FAIL: Flow '$FlowName' not found" -ForegroundColor Red
    Write-Host "Available flows:" -ForegroundColor Yellow
    $flowsResp.value | ForEach-Object { Write-Host "  - $($_.properties.displayName)" }
    exit 1
}

$flowId = $flow.name
Write-Host "Found flow: $FlowName (ID: $flowId)" -ForegroundColor Green

# Get full definition
$detail = Invoke-RestMethod -Uri "https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/$EnvironmentId/flows/$flowId" -Headers $headers
$def = $detail.properties.definition
$pass = 0
$fail = 0

function Check($name, $condition) {
    if ($condition) {
        Write-Host "  PASS: $name" -ForegroundColor Green
        $script:pass++
    } else {
        Write-Host "  FAIL: $name" -ForegroundColor Red
        $script:fail++
    }
}

Write-Host "`nChecking flow structure..." -ForegroundColor Cyan

# 1. Trigger
$trigger = $def.triggers.When_a_new_response_is_submitted
Check "Trigger exists" ($null -ne $trigger)
Check "Trigger type is OpenApiConnectionWebhook" ($trigger.type -eq "OpenApiConnectionWebhook")
Check "Trigger uses Microsoft Forms" ($trigger.inputs.host.apiId -match "microsoftforms")

# 2. Get response details
$getDetails = $def.actions.Get_response_details
Check "Get_response_details action exists" ($null -ne $getDetails)
Check "Get_response_details uses Forms connector" ($getDetails.inputs.host.apiId -match "microsoftforms")

# 3. RegisterForm HTTP action
$registerForm = $def.actions.RegisterForm
Check "RegisterForm action exists (HTTP POST)" ($null -ne $registerForm)
if ($registerForm) {
    Check "RegisterForm method is POST" ($registerForm.inputs.method -eq "POST")
    Check "RegisterForm URI contains /api/register-form" ($registerForm.inputs.uri -match "register-form")
    Check "RegisterForm has x-functions-key header" ($null -ne $registerForm.inputs.headers.'x-functions-key')
    Check "RegisterForm body has form_id" ($null -ne $registerForm.inputs.body.form_id)
    Check "RegisterForm body has raw_response" ($null -ne $registerForm.inputs.body.raw_response)
}

# 4. Condition
$condition = $def.actions.Condition
Check "Condition action exists" ($null -ne $condition)
if ($condition) {
    Check "Condition type is If" ($condition.type -eq "If")
    Check "Condition runs after RegisterForm" ($null -ne $condition.runAfter.RegisterForm)
    
    # True branch (success) - should have Entra HTTP
    $trueActions = $condition.actions
    $entraAction = $trueActions.Invoke_an_HTTP_request
    Check "True branch has Invoke_an_HTTP_request" ($null -ne $entraAction)
    if ($entraAction) {
        Check "Entra action uses webcontents connector" ($entraAction.inputs.host.apiId -match "webcontents")
        $url = $entraAction.inputs.parameters.'request/url'
        Check "Entra action URL contains /flows" ($url -match "/flows")
        Check "Entra action body references flow_create_body" ($entraAction.inputs.parameters.'request/body' -match "flow_create_body")
    }
    
    # False branch (error) - should have email
    $falseActions = $condition.else.actions
    $hasEmail = ($falseActions.PSObject.Properties | Measure-Object).Count -gt 0
    Check "False branch has error notification action" $hasEmail
}

# 5. Connection references
$connRefs = $detail.properties.connectionReferences
Check "Has Forms connection reference" ($null -ne $connRefs.shared_microsoftforms)
Check "Has Entra HTTP connection reference" ($null -ne $connRefs.shared_webcontents)

# Summary
Write-Host "`n========================================" -ForegroundColor Cyan
if ($fail -eq 0) {
    Write-Host "  ALL $pass CHECKS PASSED" -ForegroundColor Green
} else {
    Write-Host "  $pass passed, $fail FAILED" -ForegroundColor Red
}
Write-Host "========================================" -ForegroundColor Cyan

exit $fail
