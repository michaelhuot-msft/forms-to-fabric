<#
.SYNOPSIS
    Manage the form registry in Azure Blob Storage (list, remove, purge).
.DESCRIPTION
    Admin tool for testing and managing registered forms. Works directly
    with the blob-backed registry.
.EXAMPLE
    pwsh scripts/Manage-Registry.ps1 -List
.EXAMPLE
    pwsh scripts/Manage-Registry.ps1 -Remove -FormId "ePzQbQgk1k..."
.EXAMPLE
    pwsh scripts/Manage-Registry.ps1 -Purge
#>

param(
    [switch]$List,
    [switch]$Remove,
    [switch]$Purge,
    [switch]$Help,
    [string]$FormId = "",
    [string]$StorageAccount = "stformsec4zlsle",
    [string]$Container = "form-registry",
    [string]$Blob = "registry.json"
)

$ErrorActionPreference = "Stop"

# ── Help ─────────────────────────────────────────────────────────────────────

if ($Help -or (-not $List -and -not $Remove -and -not $Purge)) {
    Write-Host ""
    Write-Host "  Manage-Registry.ps1 - Admin tool for the form registry" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "  Commands:" -ForegroundColor White
    Write-Host "    -List                List all registered forms" -ForegroundColor Gray
    Write-Host "    -Remove              Interactive: pick a form to remove" -ForegroundColor Gray
    Write-Host '    -Remove -FormId "x"  Remove a specific form by ID' -ForegroundColor Gray
    Write-Host "    -Purge               Remove ALL forms (requires confirmation)" -ForegroundColor Gray
    Write-Host "    -Help                Show this help" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Examples:" -ForegroundColor White
    Write-Host "    pwsh scripts/Manage-Registry.ps1 -List" -ForegroundColor Gray
    Write-Host "    pwsh scripts/Manage-Registry.ps1 -Remove" -ForegroundColor Gray
    Write-Host "    pwsh scripts/Manage-Registry.ps1 -Purge" -ForegroundColor Gray
    Write-Host ""
    Write-Host "  Options:" -ForegroundColor White
    Write-Host '    -StorageAccount "x"  Override storage account (default: stformsec4zlsle)' -ForegroundColor Gray
    Write-Host '    -Container "x"       Override blob container (default: form-registry)' -ForegroundColor Gray
    Write-Host ""
    exit 0
}

# ── Helpers ──────────────────────────────────────────────────────────────────

function Get-Registry {
    $tempFile = [System.IO.Path]::GetTempFileName()
    az storage blob download --account-name $StorageAccount --container-name $Container --name $Blob --auth-mode key --file $tempFile --output none 2>$null
    $data = Get-Content $tempFile -Raw | ConvertFrom-Json
    Remove-Item $tempFile
    return $data
}

function Save-Registry($data) {
    $tempFile = [System.IO.Path]::GetTempFileName()
    $data | ConvertTo-Json -Depth 10 | Set-Content $tempFile -Encoding utf8
    az storage blob upload --account-name $StorageAccount --container-name $Container --name $Blob --auth-mode key --file $tempFile --overwrite --output none 2>$null
    Remove-Item $tempFile
}

# ── List ─────────────────────────────────────────────────────────────────────

if ($List) {
    Write-Host "`n=== Registered Forms ===" -ForegroundColor Cyan
    $registry = Get-Registry
    $forms = $registry.forms

    if ($forms.Count -eq 0) {
        Write-Host "  (no forms registered)" -ForegroundColor Yellow
    } else {
        # Look up deployed flows
        $deployedFlows = @{}
        try {
            $token = az account get-access-token --resource "https://service.flow.microsoft.com" --query "accessToken" -o tsv 2>$null
            if ($token) {
                $envId = "Default-6dd0fc78-2408-43d6-a255-4383fbda3f76"
                $flowHeaders = @{ "Authorization" = "Bearer $token"; "Accept" = "application/json" }
                $flowsResp = Invoke-RestMethod -Uri "https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/$envId/flows" -Headers $flowHeaders -Method GET
                foreach ($f in $flowsResp.value) {
                    $deployedFlows[$f.properties.displayName] = $f.properties.state
                }
            }
        } catch {}

        $i = 1
        foreach ($form in $forms) {
            $idShort = if ($form.form_id.Length -gt 30) { $form.form_id.Substring(0,30) + "..." } else { $form.form_id }
            $flowName = "Forms to Fabric - $($form.form_name)"
            $flowStatus = if ($deployedFlows.ContainsKey($flowName)) { $deployedFlows[$flowName] } else { "Not deployed" }
            $flowColor = if ($flowStatus -eq "Started") { "Green" } elseif ($flowStatus -eq "Stopped") { "Yellow" } else { "Red" }

            Write-Host "  $i. $($form.form_name)" -ForegroundColor White
            Write-Host "     ID:     $idShort" -ForegroundColor Gray
            Write-Host "     Table:  $($form.target_table)" -ForegroundColor Gray
            Write-Host "     Status: $($form.status)" -ForegroundColor Gray
            Write-Host "     Fields: $($form.fields.Count)" -ForegroundColor Gray
            Write-Host "     Flow:   $flowStatus" -ForegroundColor $flowColor
            Write-Host ""
            $i++
        }
    }
    Write-Host "Total: $($forms.Count) forms" -ForegroundColor Cyan
    exit 0
}

# ── Remove ───────────────────────────────────────────────────────────────────

if ($Remove) {
    if (-not $FormId) {
        # Interactive: list and let user pick
        $registry = Get-Registry
        $forms = $registry.forms

        if ($forms.Count -eq 0) {
            Write-Host "No forms to remove." -ForegroundColor Yellow
            exit 0
        }

        Write-Host "`nRegistered forms:" -ForegroundColor Cyan
        for ($i = 0; $i -lt $forms.Count; $i++) {
            $idShort = if ($forms[$i].form_id.Length -gt 30) { $forms[$i].form_id.Substring(0,30) + "..." } else { $forms[$i].form_id }
            Write-Host "  $($i+1). $($forms[$i].form_name) ($idShort)"
        }

        $choice = Read-Host "`nEnter number to remove (or 'q' to cancel)"
        if ($choice -eq 'q') { exit 0 }
        $idx = [int]$choice - 1
        if ($idx -lt 0 -or $idx -ge $forms.Count) {
            Write-Host "Invalid selection." -ForegroundColor Red
            exit 1
        }
        $FormId = $forms[$idx].form_id
    }

    $registry = Get-Registry
    $before = $registry.forms.Count
    # Find the form name before removing (for flow lookup)
    $formEntry = $registry.forms | Where-Object { $_.form_id -eq $FormId }
    $formName = if ($formEntry) { $formEntry.form_name } else { "" }

    $registry.forms = @($registry.forms | Where-Object { $_.form_id -ne $FormId })
    $after = $registry.forms.Count

    if ($before -eq $after) {
        Write-Host "Form '$FormId' not found in registry." -ForegroundColor Yellow
        exit 1
    }

    Save-Registry $registry
    Write-Host "Removed form from registry." -ForegroundColor Green

    # Clean up the auto-created PA flow
    if ($formName) {
        $flowDisplayName = "Forms to Fabric - $formName"
        Write-Host "Looking for PA flow: '$flowDisplayName'..." -ForegroundColor Cyan
        try {
            $token = az account get-access-token --resource "https://service.flow.microsoft.com" --query "accessToken" -o tsv 2>$null
            if ($token) {
                $envId = "Default-6dd0fc78-2408-43d6-a255-4383fbda3f76"
                $flowHeaders = @{ "Authorization" = "Bearer $token"; "Accept" = "application/json" }
                $flowsResp = Invoke-RestMethod -Uri "https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/$envId/flows" -Headers $flowHeaders -Method GET
                $matchingFlow = $flowsResp.value | Where-Object { $_.properties.displayName -eq $flowDisplayName }
                if ($matchingFlow) {
                    $flowId = $matchingFlow.name
                    Invoke-RestMethod -Uri "https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/$envId/flows/$flowId" -Headers $flowHeaders -Method DELETE | Out-Null
                    Write-Host "Deleted PA flow: $flowDisplayName (ID: $flowId)" -ForegroundColor Green
                } else {
                    Write-Host "No matching PA flow found (may not have been auto-created)." -ForegroundColor Yellow
                }
            }
        } catch {
            Write-Host "Could not clean up PA flow: $($_.Exception.Message)" -ForegroundColor Yellow
            Write-Host "You may need to delete '$flowDisplayName' manually in Power Automate." -ForegroundColor Yellow
        }
    }

    Write-Host "Registry now has $after forms." -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Note: Data tables in Fabric Lakehouse are NOT deleted automatically." -ForegroundColor Yellow
    Write-Host "To remove the data, go to your Fabric Lakehouse and delete:" -ForegroundColor Yellow
    Write-Host "  Tables/$($formEntry.target_table)_raw" -ForegroundColor White
    Write-Host "  Tables/$($formEntry.target_table)_curated (if it exists)" -ForegroundColor White
    exit 0
}

# ── Purge ────────────────────────────────────────────────────────────────────

if ($Purge) {
    $registry = Get-Registry
    $count = $registry.forms.Count

    if ($count -eq 0) {
        Write-Host "Registry is already empty." -ForegroundColor Yellow
        exit 0
    }

    Write-Host "`nThis will remove ALL $count registered forms:" -ForegroundColor Red
    foreach ($form in $registry.forms) {
        Write-Host "  - $($form.form_name) ($($form.form_id.Substring(0, [Math]::Min(30, $form.form_id.Length)))...)" -ForegroundColor Yellow
    }

    $confirm = Read-Host "`nType 'PURGE' to confirm"
    if ($confirm -ne 'PURGE') {
        Write-Host "Cancelled." -ForegroundColor Yellow
        exit 0
    }

    # Clean up auto-created PA flows
    Write-Host "`nCleaning up PA flows..." -ForegroundColor Cyan
    try {
        $token = az account get-access-token --resource "https://service.flow.microsoft.com" --query "accessToken" -o tsv 2>$null
        if ($token) {
            $envId = "Default-6dd0fc78-2408-43d6-a255-4383fbda3f76"
            $flowHeaders = @{ "Authorization" = "Bearer $token"; "Accept" = "application/json" }
            $flowsResp = Invoke-RestMethod -Uri "https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/$envId/flows" -Headers $flowHeaders -Method GET
            foreach ($form in $registry.forms) {
                $flowDisplayName = "Forms to Fabric - $($form.form_name)"
                $matchingFlow = $flowsResp.value | Where-Object { $_.properties.displayName -eq $flowDisplayName }
                if ($matchingFlow) {
                    $flowId = $matchingFlow.name
                    Invoke-RestMethod -Uri "https://api.flow.microsoft.com/providers/Microsoft.ProcessSimple/environments/$envId/flows/$flowId" -Headers $flowHeaders -Method DELETE | Out-Null
                    Write-Host "  Deleted flow: $flowDisplayName" -ForegroundColor Green
                }
            }
        }
    } catch {
        Write-Host "  Could not clean up flows: $($_.Exception.Message)" -ForegroundColor Yellow
        Write-Host "  Delete 'Forms to Fabric - ...' flows manually in Power Automate." -ForegroundColor Yellow
    }

    # Save table names before purging (for the reminder)
    $tableNames = $registry.forms | ForEach-Object { $_.target_table }

    $registry.forms = @()
    Save-Registry $registry
    Write-Host "Purged all $count forms from registry." -ForegroundColor Green
    Write-Host ""
    Write-Host "Note: Data tables in Fabric Lakehouse are NOT deleted automatically." -ForegroundColor Yellow
    Write-Host "To remove the data, go to your Fabric Lakehouse and delete these tables:" -ForegroundColor Yellow
    foreach ($t in $tableNames) {
        Write-Host "  Tables/${t}_raw" -ForegroundColor White
        Write-Host "  Tables/${t}_curated" -ForegroundColor White
    }
    exit 0
}
