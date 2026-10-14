# Morning SEO routine: local public checks + optional production metadata audit via GitHub Actions.
#
# Usage:
#   .\scripts\run-daily-seo.ps1
#   .\scripts\run-daily-seo.ps1 -TriggerProdAudit
#
# Prod audit runs workflow "Run Odoo shell on production" (read-only script). One shell at a time.
param(
    [switch]$TriggerProdAudit
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot

Write-Host ""
Write-Host "Re-Ware daily SEO routine" -ForegroundColor Cyan
Write-Host ""

& (Join-Path $PSScriptRoot "daily_seo_check.ps1")
$localExit = $LASTEXITCODE

if (-not $TriggerProdAudit) {
    Write-Host ""
    Write-Host "Local checks finished (exit $localExit)." -ForegroundColor Gray
    Write-Host "For Odoo SEO metadata (published products/pages), run:" -ForegroundColor Gray
    Write-Host '  .\scripts\run-daily-seo.ps1 -TriggerProdAudit' -ForegroundColor Gray
    Write-Host "  or GitHub Actions -> Run Odoo shell -> script: audit_seo_metadata_shell.py" -ForegroundColor Gray
    exit $localExit
}

$running = gh run list --limit 20 --json status,name,url |
    ConvertFrom-Json |
    Where-Object {
        $_.status -in @("queued", "in_progress", "pending", "waiting") -and
        $_.name -match "Deploy production|Repair production|Run Odoo shell"
    }

if ($running) {
    Write-Host ""
    Write-Host "Skipped prod audit — another production job is active:" -ForegroundColor Yellow
    $running | ForEach-Object { Write-Host ("  [{0}] {1}  {2}" -f $_.status, $_.name, $_.url) }
    exit $localExit
}

Write-Host ""
Write-Host "Triggering production Odoo shell: audit_seo_metadata_shell.py ..."
gh workflow run "Run Odoo shell on production" --ref main -f script=audit_seo_metadata_shell.py

Start-Sleep -Seconds 4
$run = gh run list --workflow="Run Odoo shell on production" --limit 1 --json databaseId,url,status | ConvertFrom-Json
if ($run) {
    Write-Host "Workflow: $($run.url)"
    Write-Host "Watch: gh run watch $($run.databaseId) --exit-status"
} else {
    Write-Host "Workflow triggered — check: gh run list --workflow `"Run Odoo shell on production`""
}

exit $localExit
