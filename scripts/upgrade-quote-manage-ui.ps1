# Upgrade quote_manage_ui via Docker (Windows PowerShell).
# Usage: .\scripts\upgrade-quote-manage-ui.ps1

# `docker compose` writes informational lines to stderr; PowerShell would
# otherwise treat that as a fatal error with NativeCommandError. Use
# Continue so we only stop on actual non-zero exit codes (checked below).
$ErrorActionPreference = "Continue"
Set-Location (Split-Path $PSScriptRoot -Parent)

$Db = if ($env:ODOO_DATABASE) { $env:ODOO_DATABASE } else { "cocreativeit-quote" }
$Module = if ($env:ODOO_MODULE) { $env:ODOO_MODULE } else { "quote_manage_ui" }

Write-Host "Upgrading module $Module on database $Db..."
docker compose run --rm web odoo -c /etc/odoo/odoo.conf -d $Db -u $Module --stop-after-init 2>&1 | Out-Host
if ($LASTEXITCODE -ne 0) { Write-Host "Upgrade failed with exit $LASTEXITCODE"; exit $LASTEXITCODE }

Write-Host "Syncing locked snippet/template views from XML..."
Get-Content "$PSScriptRoot\sync_rw_templates.py" | docker compose run --rm -T web odoo shell -c /etc/odoo/odoo.conf -d $Db --stop-after-init 2>&1 | Out-Host

docker compose restart web nginx 2>&1 | Out-Host
Write-Host "Done."
