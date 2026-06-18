# Backup Odoo PostgreSQL database before product import (DESTRUCTIVE-CHANGE safety net).
# Uses gzip inside the db container (no Windows gzip required).
# Usage:
#   .\scripts\backup_odoo_db.ps1
#   .\scripts\backup_odoo_db.ps1 -Database cocreativeit-quote -Label before-merged-import
param(
    [string]$Database = $(if ($env:ODOO_DATABASE) { $env:ODOO_DATABASE } else { "cocreativeit-quote" }),
    [string]$Label = "manual"
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root

$BackupDir = Join-Path $Root "backups"
New-Item -ItemType Directory -Force -Path $BackupDir | Out-Null
$Stamp = Get-Date -Format "yyyyMMdd-HHmmss"
$OutFile = Join-Path $BackupDir "db-$Label-$Stamp.sql.gz"
$ContainerPath = "/tmp/odoo-backup-$Stamp.sql.gz"

Write-Host "[backup] Database: $Database"
Write-Host "[backup] Writing: $OutFile"

docker compose exec -T db sh -c "pg_dump -U odoo '$Database' | gzip -c > '$ContainerPath'"
if ($LASTEXITCODE -ne 0) {
    throw "pg_dump inside container failed (exit $LASTEXITCODE)"
}

docker compose cp "db:$ContainerPath" $OutFile
if ($LASTEXITCODE -ne 0) {
    throw "docker compose cp failed (exit $LASTEXITCODE)"
}

docker compose exec -T db rm -f $ContainerPath | Out-Null

$size = (Get-Item $OutFile).Length
Write-Host "[backup] Done. Size bytes: $size"
Write-Host "[backup] Restore with: .\scripts\restore_odoo_db.ps1 -BackupFile `"$OutFile`""
