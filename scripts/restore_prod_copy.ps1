# Restore production backup into cocreativeit-quote-prod-copy (does NOT touch cocreativeit-quote).
param(
    [string]$BackupFile = "backups\cocreativeit-quote-prod-20260624.sql.gz"
)
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $PSScriptRoot
Set-Location $Root
$BackupFile = (Resolve-Path $BackupFile).Path
$ContainerDump = "/tmp/odoo-prod-copy-restore.sql.gz"
$DbName = "cocreativeit_quote_prod_copy"

Write-Host "[restore-prod-copy] Backup: $BackupFile"
Write-Host "[restore-prod-copy] Target DB: $DbName"

docker compose cp $BackupFile "db:$ContainerDump"
docker compose exec -T db psql -U odoo -d postgres -c "DROP DATABASE IF EXISTS $DbName;"
docker compose exec -T db psql -U odoo -d postgres -c "CREATE DATABASE $DbName OWNER odoo;"
docker compose exec -T db sh -c "gunzip -c /tmp/odoo-prod-copy-restore.sql.gz | psql -U odoo -d $DbName"
docker compose exec -T db rm -f $ContainerDump
Write-Host "[restore-prod-copy] Done."
