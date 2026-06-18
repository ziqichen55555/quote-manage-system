# Restore Odoo DB from a gzip pg_dump created by backup_odoo_db.ps1
# WARNING: OVERWRITES the target database. Stop web first on production.
# Uses gzip inside the db container (no Windows gzip required).
# Usage:
#   .\scripts\restore_odoo_db.ps1 -BackupFile backups\db-before-merged-import-20260618.sql.gz
param(
    [Parameter(Mandatory = $true)]
    [string]$BackupFile,
    [string]$Database = $(if ($env:ODOO_DATABASE) { $env:ODOO_DATABASE } else { "cocreativeit-quote" })
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
$confirm = Read-Host "Type RESTORE to continue"
if ($confirm -ne "RESTORE") {
    Write-Host "Aborted."
    exit 1
}

$ContainerPath = "/tmp/odoo-restore.sql.gz"

Write-Host "[restore] Stopping web container..."
docker compose stop web 2>$null

Write-Host "[restore] Dropping and recreating database..."
docker compose exec -T db psql -U odoo -d postgres -c "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = '$Database' AND pid <> pg_backend_pid();"
docker compose exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS `"$Database`";"
docker compose exec -T db psql -U odoo -d postgres -c "CREATE DATABASE `"$Database`" OWNER odoo;"

Write-Host "[restore] Loading dump..."
if ($BackupFile -match '\.gz$') {
    docker compose cp $BackupFile "db:$ContainerPath"
    if ($LASTEXITCODE -ne 0) { throw "docker compose cp failed" }
    docker compose exec -T db sh -c "gunzip -c '$ContainerPath' | psql -U odoo -d '$Database'"
    if ($LASTEXITCODE -ne 0) { throw "pg_restore via psql failed" }
    docker compose exec -T db rm -f $ContainerPath | Out-Null
} elseif ($BackupFile -match '\.dump$') {
    docker compose cp $BackupFile "db:$ContainerPath"
    docker compose exec -T db pg_restore -U odoo -d $Database --no-owner --clean --if-exists $ContainerPath
    docker compose exec -T db rm -f $ContainerPath | Out-Null
} else {
    Get-Content $BackupFile -Raw | docker compose exec -T db psql -U odoo -d $Database
}

Write-Host "[restore] Starting web..."
docker compose start web
Write-Host "[restore] Done. Verify /shop and a few product images/prices."
