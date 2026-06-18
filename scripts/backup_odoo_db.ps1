# Backup Odoo PostgreSQL database before product import (DESTRUCTIVE-CHANGE safety net).
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

Write-Host "[backup] Database: $Database"
Write-Host "[backup] Writing: $OutFile"

docker compose exec -T db pg_dump -U odoo $Database | gzip > $OutFile
if ($LASTEXITCODE -ne 0) {
    throw "pg_dump failed (exit $LASTEXITCODE)"
}

$size = (Get-Item $OutFile).Length
Write-Host "[backup] Done. Size bytes: $size"
Write-Host "[backup] Restore with: .\scripts\restore_odoo_db.ps1 -BackupFile `"$OutFile`""
