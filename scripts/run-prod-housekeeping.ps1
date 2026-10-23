# Upload and run prod-housekeeping.sh on DigitalOcean (dry-run by default).
#
# Usage (repo root):
#   .\scripts\run-prod-housekeeping.ps1
#   .\scripts\run-prod-housekeeping.ps1 -ConfirmApply APPLY
#   .\scripts\run-prod-housekeeping.ps1 -ConfirmApply APPLY -DropCaches
#
param(
    [string]$ConfirmApply = "",
    [switch]$DropCaches,
    [string]$SshHost = "root@134.199.145.67",
    [string]$SshKey = "$env:USERPROFILE\.ssh\id_ed25519_do",
    [string]$RemoteDir = "/root/reware/scripts"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
$LocalScript = Join-Path $PSScriptRoot "prod-housekeeping.sh"

if (-not (Test-Path $LocalScript)) {
    Write-Error "Missing $LocalScript"
}
if (-not (Test-Path $SshKey)) {
    Write-Error "SSH key not found: $SshKey"
}

$apply = $ConfirmApply -eq "APPLY"
if (-not $apply) {
    Write-Host "Dry-run on $SshHost (no changes). To apply: -ConfirmApply APPLY" -ForegroundColor Yellow
}

$sshArgs = @("-i", $SshKey, "-o", "ConnectTimeout=20", "-o", "StrictHostKeyChecking=accept-new")

Write-Host "[housekeeping] Upload script..."
& scp @sshArgs $LocalScript "${SshHost}:${RemoteDir}/prod-housekeeping.sh"

# Strip CRLF if the file was edited on Windows.
& ssh @sshArgs $SshHost "sed -i 's/\r$//' ${RemoteDir}/prod-housekeeping.sh"

$remoteCmd = "chmod +x ${RemoteDir}/prod-housekeeping.sh && "
if ($apply) {
    $remoteCmd += "DRY_RUN=0 CONFIRM=APPLY "
    if ($DropCaches) {
        $remoteCmd += "DROP_CACHES=1 "
    }
    $remoteCmd += "${RemoteDir}/prod-housekeeping.sh --apply"
    if ($DropCaches) {
        $remoteCmd += " --drop-caches"
    }
} else {
    $remoteCmd += "${RemoteDir}/prod-housekeeping.sh"
}

Write-Host "[housekeeping] Run on server..."
& ssh @sshArgs $SshHost $remoteCmd
