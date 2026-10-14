# Register a Windows Task Scheduler job: weekdays 9:00 AM, local SEO checks only.
# Run once from an elevated PowerShell if your policy requires it for schtasks.
#
# Usage:
#   .\scripts\register-daily-seo-task.ps1
#   .\scripts\register-daily-seo-task.ps1 -Time "08:30" -Unregister

param(
    [string]$Time = "09:00",
    [switch]$Unregister
)

$ErrorActionPreference = "Stop"
$TaskName = "ReWare-Daily-SEO-Local"
$RepoRoot = Split-Path -Parent $PSScriptRoot
$Script = Join-Path $RepoRoot "scripts\daily_seo_check.ps1"
$LogDir = Join-Path $RepoRoot "scripts\logs"
$LogFile = Join-Path $LogDir "daily_seo_check.log"

if ($Unregister) {
    schtasks /Delete /TN $TaskName /F 2>$null
    Write-Host "Removed scheduled task: $TaskName"
    exit 0
}

if (-not (Test-Path $Script)) {
    Write-Error "Missing script: $Script"
}

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

$pwsh = (Get-Command pwsh -ErrorAction SilentlyContinue).Source
if (-not $pwsh) {
    $pwsh = (Get-Command powershell.exe).Source
}

# Append output to log; task runs even if user is not logged in (best-effort with /IT for interactive logon).
$action = "powershell.exe -NoProfile -ExecutionPolicy Bypass -Command `"& '$Script' *>> '$LogFile'`""
schtasks /Create /F /TN $TaskName /SC WEEKLY /D MON,TUE,WED,THU,FRI /ST $Time /TR $action /RL LIMITED

Write-Host "Created task: $TaskName"
Write-Host "  When: Mon–Fri at $Time"
Write-Host "  Runs: $Script"
Write-Host "  Log:  $LogFile"
Write-Host ""
Write-Host "Manual run anytime: .\scripts\run-daily-seo.ps1"
