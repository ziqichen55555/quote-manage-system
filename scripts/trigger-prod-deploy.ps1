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

# Block if another prod job is already running
$running = gh run list --limit 20 --json status,name,databaseId,url |
    ConvertFrom-Json |
    Where-Object { $_.status -in @("queued", "in_progress", "pending", "waiting") -and $_.name -match "Deploy production|Repair production|Run Odoo shell" }

if ($running) {
    Write-Host "Blocked — production job already active:" -ForegroundColor Yellow
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

Start-Sleep -Seconds 3
$run = gh run list --workflow="Deploy production" --limit 1 --json databaseId,url,status,displayTitle | ConvertFrom-Json
if (-not $run) {
    Fail "Workflow triggered but no run found yet — check: gh run list --workflow `"Deploy production`""
}

Write-Host ""
Write-Host "Triggered: $($run[0].displayTitle)"
Write-Host "Status:    $($run[0].status)"
Write-Host "Watch:     gh run watch $($run[0].databaseId)"
Write-Host "URL:       $($run[0].url)"
Write-Host ""
Write-Host "Tip: gh run watch $($run[0].databaseId) --exit-status"
