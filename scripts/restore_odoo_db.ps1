# Restore Odoo DB from a gzip pg_dump created by backup_odoo_db.ps1
# WARNING: OVERWRITES the target database. Stop web first on production.
# Usage:
#   .\scripts\restore_odoo_db.ps1 -BackupFile backups\db-before-merged-import-20260618.sql.gz
#   .\scripts\restore_odoo_db.ps1 -BackupFile backups\....sql.gz -Force
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [string]$Database = $(if ($env:ODOO_DATABASE) { $env:ODOO_DATABASE } else { "cocreativeit-quote" }),
    [switch]$Force
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$BackupFile = (Resolve-Path $BackupFile).Path
if (-not (Test-Path $BackupFile)) {
    throw "Backup file not found: $BackupFile"
}

Write-Host "[restore] WARNING: This will REPLACE database '$Database'."
Write-Host "[restore] Backup: $BackupFile"
if (-not $Force) {
    $confirm = Read-Host "Type RESTORE to continue"
    if ($confirm -ne "RESTORE") {
        Write-Host "Aborted."
        exit 1
    }
}

$ContainerPath = "/tmp/odoo-restore.sql.gz"
$RestoreScript = "/tmp/restore_db_inside.sh"

Write-Host "[restore] Stopping web container..."
$prevEap = $ErrorActionPreference
$ErrorActionPreference = "Continue"
docker compose stop web 2>&1 | Out-Null
$ErrorActionPreference = $prevEap

Write-Host "[restore] Dropping, recreating, and loading database..."
$RestorePy = Join-Path $PSScriptRoot "restore_backup_now.py"
if (Test-Path $RestorePy) {
    & python $RestorePy $BackupFile
    if ($LASTEXITCODE -ne 0) { throw "restore_backup_now.py failed" }
    exit 0
}

docker compose cp $BackupFile "db:$ContainerPath"
if ($LASTEXITCODE -ne 0) { throw "docker compose cp (dump) failed" }
docker compose cp "scripts/restore_db_inside.sh" "db:$RestoreScript"
if ($LASTEXITCODE -ne 0) { throw "docker compose cp (script) failed" }
docker compose exec -T db sh "$RestoreScript" "$Database" "$ContainerPath"
if ($LASTEXITCODE -ne 0) { throw "restore_db_inside.sh failed" }

Write-Host "[restore] Starting web..."curl -I https://www.reware-project.com/

docker compose start web
Write-Host "[restore] Done. Upgrade quote_manage_ui, then re-upload MERGED CSV (additive)."
