# Trigger production Deploy from Cursor / local machine (no GitHub UI).
# Requires: gh CLI authenticated; confirm by typing DEPLOY when prompted
#   (or pass -ConfirmDeploy DEPLOY for non-interactive agent use after user OK).
#
# Usage:
#   .\scripts\trigger-prod-deploy.ps1
#   .\scripts\trigger-prod-deploy.ps1 -ConfirmDeploy DEPLOY
param(
    [string]$ConfirmDeploy = ""
)

$ErrorActionPreference = "Stop"

function Fail([string]$msg) {
    Write-Host "ERROR: $msg" -ForegroundColor Red
    exit 1
}

function ConvertFrom-GhJsonArray {
    param([AllowNull()][string]$Raw)
    if (-not $Raw -or -not $Raw.Trim()) {
        return @()
    }
    $parsed = $Raw | ConvertFrom-Json
    if ($null -eq $parsed) {
        return @()
    }
    if ($parsed -is [System.Array]) {
        return @($parsed)
    }
    return @($parsed)
}

function Get-LatestDeployRun {
    $raw = gh run list --workflow="Deploy production" --limit 1 `
        --json databaseId,url,status,displayTitle 2>&1 | Out-String
    $items = ConvertFrom-GhJsonArray $raw.Trim()
    if ($items.Count -lt 1) {
        return $null
    }
    return $items[0]
}

# Block if another prod job is already running
$listRaw = gh run list --limit 20 --json status,name,databaseId,url 2>&1 | Out-String
$allRuns = ConvertFrom-GhJsonArray $listRaw.Trim()
$running = @($allRuns | Where-Object {
    $_.status -in @("queued", "in_progress", "pending", "waiting") -and
    $_.name -match "Deploy production|Repair production|Run Odoo shell"
})

if ($running.Count -gt 0) {
    Write-Host "Blocked - production job already active:" -ForegroundColor Yellow
    $running | ForEach-Object { Write-Host ("  [{0}] {1}  {2}" -f $_.status, $_.name, $_.url) }
    Fail "Wait for it to finish (or Repair if stuck), then retry."
}

if ($ConfirmDeploy -ne "DEPLOY") {
    Write-Host ""
    Write-Host "This will upload custom_addons and run odoo -u on production."
    Write-Host "Site: https://www.reware-project.com"
    Write-Host ""
    $ConfirmDeploy = Read-Host "Type DEPLOY to continue (anything else aborts)"
}

if ($ConfirmDeploy -ne "DEPLOY") {
    Fail "Aborted (expected DEPLOY)."
}

Write-Host "Starting Deploy production (confirm_deploy=DEPLOY)..."
gh workflow run "Deploy production" --ref main -f confirm_deploy=DEPLOY

$run = $null
foreach ($attempt in 1..12) {
    Start-Sleep -Seconds 5
    $run = Get-LatestDeployRun
    if ($run -and $run.databaseId -and $run.status -in @("queued", "in_progress", "pending", "waiting", "completed")) {
        break
    }
}

Write-Host ""
if (-not $run -or -not $run.databaseId) {
    Write-Host "Deploy workflow was triggered." -ForegroundColor Green
    Write-Host "GitHub has not listed the run yet (normal for 30-60 seconds)." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "Check status:"
    Write-Host '  gh run list --workflow "Deploy production" --limit 3'
    Write-Host "  gh run watch <id> --exit-status"
    exit 0
}

Write-Host ("Triggered: {0}" -f $run.displayTitle)
Write-Host ("Status:    {0}" -f $run.status)
Write-Host ("Watch:     gh run watch {0} --exit-status" -f $run.databaseId)
Write-Host ("URL:       {0}" -f $run.url)
Write-Host ""
