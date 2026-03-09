<#
.SYNOPSIS
    Creates the self-service registration Power Automate flow.
.DESCRIPTION
    One-time setup script that programmatically creates the "Forms to Fabric:
    Register New Form" cloud flow in Power Automate.  This flow listens to a
    registration Microsoft Form, calls /api/register-form, and on success
    creates the per-form data pipeline flow via the Flow Management API.

    Prerequisites:
    - Azure CLI authenticated (az login)
    - Registration Microsoft Form already created
    - Azure Function App deployed (azd up completed)
    - Microsoft Forms, Office 365 Outlook, and HTTP with Microsoft Entra ID
      connections created in Power Automate
.PARAMETER RegistrationFormId
    The Microsoft Form ID for the "Register Your Form" intake form.
    If not provided, the script will prompt you.
.PARAMETER FunctionAppUrl
    Azure Function App base URL.  Auto-detected from the resource group.
.PARAMETER FunctionAppKey
    Function or host key.  Auto-detected from the Function App.
.PARAMETER AlertEmail
    Admin notification email.  Auto-detected from az login.
.PARAMETER FormsConnectionName
    Power Automate connection name for Microsoft Forms.
.PARAMETER OutlookConnectionName
    Power Automate connection name for Office 365 Outlook.
.PARAMETER WebContentsConnectionName
    Power Automate connection name for HTTP with Microsoft Entra ID.
.PARAMETER DryRun
    Print the flow definition JSON without creating the flow.
.EXAMPLE
    pwsh scripts/Create-RegistrationFlow.ps1
.EXAMPLE
    pwsh scripts/Create-RegistrationFlow.ps1 -RegistrationFormId "v4j5cvGGr0G..."
.EXAMPLE
    pwsh scripts/Create-RegistrationFlow.ps1 -DryRun
#>

param(
    [string]$RegistrationFormId       = "",
    [string]$RegistrationFormUrl      = "",
    [string]$FunctionAppUrl           = "",
    [string]$FunctionAppKey           = "",
    [string]$AlertEmail               = "",
    [string]$FormsConnectionName      = "shared_microsoftforms",
    [string]$OutlookConnectionName    = "shared_office365",
    [string]$WebContentsConnectionName = "shared_webcontents",
    [string]$ResourceGroup            = "rg-forms-to-fabric-dev",
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  Forms to Fabric - Create Registration Flow" -ForegroundColor Cyan
Write-Host "========================================`n" -ForegroundColor Cyan

# ── Step 1: Resolve Registration Form ID ────────────────────────────────────

if (-not $RegistrationFormId -and $RegistrationFormUrl) {
    if ($RegistrationFormUrl -match "[?&]id=([^&]+)") {
        $RegistrationFormId = $Matches[1]
    } elseif ($RegistrationFormUrl -match "/r/([A-Za-z0-9_-]+)") {
        $RegistrationFormId = $Matches[1]
    }
}

if (-not $RegistrationFormId) {
    Write-Host "Step 1: Registration Form ID" -ForegroundColor Yellow
    Write-Host "  Paste the URL of your 'Register Your Form for Analytics' Microsoft Form."
    Write-Host "  (See docs/registration-form-template.md for setup instructions.)`n"
    $url = Read-Host "  Registration Form URL or Form ID"
    if ($url -match "[?&]id=([^&]+)") {
        $RegistrationFormId = $Matches[1]
    } elseif ($url -match "/r/([A-Za-z0-9_-]+)") {
        $RegistrationFormId = $Matches[1]
    } else {
        $RegistrationFormId = $url
    }
}

if (-not $RegistrationFormId) {
    Write-Host "ERROR: Could not determine Registration Form ID." -ForegroundColor Red
    exit 1
}
Write-Host "  Registration Form ID: $RegistrationFormId" -ForegroundColor Green

# ── Step 2: Resolve Function App URL and Key ────────────────────────────────

$funcAppName = $null

if (-not $FunctionAppUrl -or -not $FunctionAppKey) {
    Write-Host "`nStep 2: Detecting Function App..." -ForegroundColor Yellow
    try {
        $funcAppName = az functionapp list --resource-group $ResourceGroup --query "[0].name" -o tsv 2>$null
    } catch {}

    if ($funcAppName) {
        if (-not $FunctionAppUrl) {
            $hostName = az functionapp show --name $funcAppName --resource-group $ResourceGroup --query "defaultHostName" -o tsv 2>$null
            if ($hostName) {
                $FunctionAppUrl = "https://$hostName"
            }
        }
        if (-not $FunctionAppKey) {
            $FunctionAppKey = az functionapp keys list --name $funcAppName --resource-group $ResourceGroup --query "functionKeys.default" -o tsv 2>$null
        }
    }
}

if (-not $FunctionAppUrl) {
    $FunctionAppUrl = Read-Host "  Enter Function App URL (e.g., https://func-forms-dev-abc.azurewebsites.net)"
}
if (-not $FunctionAppKey) {
    $FunctionAppKey = Read-Host "  Enter Function App key"
}

Write-Host "  Function App: $FunctionAppUrl" -ForegroundColor Green
Write-Host "  Function Key: (detected)" -ForegroundColor Green

# ── Step 3: Resolve alert email ─────────────────────────────────────────────

if (-not $AlertEmail) {
    try {
        $AlertEmail = az account show --query "user.name" -o tsv 2>$null
    } catch {}
}
if (-not $AlertEmail) {
    $AlertEmail = Read-Host "  Enter admin notification email"
}
Write-Host "  Alert Email:  $AlertEmail" -ForegroundColor Green

# ── Step 4: Resolve Power Platform environment ID ───────────────────────────

Write-Host "`nStep 3: Resolving Power Platform environment..." -ForegroundColor Yellow
$tenantId = az account show --query "tenantId" -o tsv 2>$null
if (-not $tenantId) {
    $tenantId = Read-Host "  Enter your Azure AD tenant ID"
}
$flowEnvironmentId = "Default-$tenantId"
Write-Host "  Flow Environment: $flowEnvironmentId" -ForegroundColor Green

# ── Step 5: Confirm configuration ──────────────────────────────────────────

Write-Host "`n────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  Configuration Summary" -ForegroundColor Cyan
Write-Host "────────────────────────────────────────" -ForegroundColor DarkGray
Write-Host "  Registration Form ID:   $RegistrationFormId"
Write-Host "  Function App URL:       $FunctionAppUrl"
Write-Host "  Function App Key:       ****$(if ($FunctionAppKey.Length -gt 4) { $FunctionAppKey.Substring($FunctionAppKey.Length - 4) } else { '****' })"
Write-Host "  Alert Email:            $AlertEmail"
Write-Host "  Flow Environment:       $flowEnvironmentId"
Write-Host "  Forms Connection:       $FormsConnectionName"
Write-Host "  Outlook Connection:     $OutlookConnectionName"
Write-Host "  WebContents Connection: $WebContentsConnectionName"
Write-Host "────────────────────────────────────────" -ForegroundColor DarkGray

if (-not $DryRun) {
    Write-Host "`n  This will create the registration flow in Power Automate." -ForegroundColor Yellow
    Write-Host "  The flow will start immediately and listen for form submissions.`n" -ForegroundColor Yellow
}

$confirm = Read-Host "  Proceed? (y/N)"
if ($confirm -notmatch "^[yY]") {
    Write-Host "`n  Cancelled." -ForegroundColor Yellow
    exit 0
}

# ── Step 6: Create the flow ────────────────────────────────────────────────

Write-Host "`nStep 4: Creating registration flow..." -ForegroundColor Yellow

$pyArgs = @(
    "scripts/create_registration_flow.py",
    "--registration-form-id", $RegistrationFormId,
    "--function-app-url", $FunctionAppUrl,
    "--function-app-key", $FunctionAppKey,
    "--flow-environment-id", $flowEnvironmentId,
    "--alert-email", $AlertEmail,
    "--forms-connection", $FormsConnectionName,
    "--outlook-connection", $OutlookConnectionName,
    "--webcontents-connection", $WebContentsConnectionName
)

if ($DryRun) {
    $pyArgs += "--dry-run"
}

$result = python @pyArgs

if ($LASTEXITCODE -ne 0) {
    Write-Host "`nERROR: Flow creation failed." -ForegroundColor Red
    Write-Host $result -ForegroundColor Red
    exit 1
}

if ($DryRun) {
    Write-Host $result
    Write-Host "`n  Dry run complete. No flow was created." -ForegroundColor Yellow
} else {
    try {
        $parsed = $result | ConvertFrom-Json
        Write-Host "`n========================================" -ForegroundColor Green
        Write-Host "  Registration flow created!" -ForegroundColor Green
        Write-Host "========================================" -ForegroundColor Green
        Write-Host "  Flow ID: $($parsed.flow_id)" -ForegroundColor White
        Write-Host "  State:   $($parsed.state)" -ForegroundColor White

        # Store the flow ID in azd env for teardown
        try {
            azd env set REGISTRATION_FLOW_ID $parsed.flow_id 2>$null
            Write-Host "`n  Saved REGISTRATION_FLOW_ID to azd env for teardown." -ForegroundColor Green
        } catch {
            Write-Host "  (Could not save to azd env — note the flow ID above for manual teardown)" -ForegroundColor Yellow
        }
    } catch {
        Write-Host $result
    }

    Write-Host "`n  Next steps:" -ForegroundColor Cyan
    Write-Host "  1. Verify in Power Automate portal: https://make.powerautomate.com" -ForegroundColor White
    Write-Host "  2. Check that connections are authorized (may need one-time consent)" -ForegroundColor White
    Write-Host "  3. Test by submitting a registration form" -ForegroundColor White
}

Write-Host ""
