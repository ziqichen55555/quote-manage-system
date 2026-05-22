# Start a free Cloudflare Quick Tunnel to expose local Odoo to the public.
# Usage: .\scripts\start-tunnel.ps1
# Press Ctrl+C to stop.
# URL changes every time you (re)start; copy it from the output and share.

$ErrorActionPreference = "Stop"
Set-Location (Split-Path $PSScriptRoot -Parent)

if (-not (Test-Path .\cloudflared.exe)) {
    Write-Host "Downloading cloudflared.exe ..."
    Invoke-WebRequest -Uri "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe" -OutFile ".\cloudflared.exe"
}

# Sanity check: is Odoo / nginx actually serving locally?
$target = "http://localhost:8070"
try {
    $null = Invoke-WebRequest -Uri $target -UseBasicParsing -TimeoutSec 3
} catch {
    Write-Host "Local site at $target does not respond. Trying 8069 (Odoo direct) ..."
    try {
        $null = Invoke-WebRequest -Uri "http://localhost:8069" -UseBasicParsing -TimeoutSec 3
        $target = "http://localhost:8069"
    } catch {
        Write-Host "Neither 8070 nor 8069 responds. Start Docker first: docker compose up -d"
        exit 1
    }
}

Write-Host ""
Write-Host "Starting Cloudflare Quick Tunnel -> $target"
Write-Host "Look for a line like:  https://xxx-xxx-xxx.trycloudflare.com"
Write-Host "Share that URL. Press Ctrl+C to stop."
Write-Host ""

& .\cloudflared.exe tunnel --url $target
