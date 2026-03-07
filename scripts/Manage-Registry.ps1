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
    [string]$FormId = "",
    [string]$StorageAccount = "stformsec4zlsle",
    [string]$Container = "form-registry",
    [string]$Blob = "registry.json"
)

$ErrorActionPreference = "Stop"

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
        $i = 1
        foreach ($form in $forms) {
            $idShort = if ($form.form_id.Length -gt 30) { $form.form_id.Substring(0,30) + "..." } else { $form.form_id }
            Write-Host "  $i. $($form.form_name)" -ForegroundColor White
            Write-Host "     ID:     $idShort" -ForegroundColor Gray
            Write-Host "     Table:  $($form.target_table)" -ForegroundColor Gray
            Write-Host "     Status: $($form.status)" -ForegroundColor Gray
            Write-Host "     Fields: $($form.fields.Count)" -ForegroundColor Gray
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
    $registry.forms = @($registry.forms | Where-Object { $_.form_id -ne $FormId })
    $after = $registry.forms.Count

    if ($before -eq $after) {
        Write-Host "Form '$FormId' not found in registry." -ForegroundColor Yellow
        exit 1
    }

    Save-Registry $registry
    Write-Host "Removed form: $FormId" -ForegroundColor Green
    Write-Host "Registry now has $after forms." -ForegroundColor Cyan
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

    $registry.forms = @()
    Save-Registry $registry
    Write-Host "Purged all $count forms from registry." -ForegroundColor Green
    exit 0
}

# ── No action ────────────────────────────────────────────────────────────────

Write-Host "Usage:" -ForegroundColor Cyan
Write-Host "  pwsh scripts/Manage-Registry.ps1 -List" -ForegroundColor White
Write-Host "  pwsh scripts/Manage-Registry.ps1 -Remove" -ForegroundColor White
Write-Host "  pwsh scripts/Manage-Registry.ps1 -Remove -FormId '<id>'" -ForegroundColor White
Write-Host "  pwsh scripts/Manage-Registry.ps1 -Purge" -ForegroundColor White
