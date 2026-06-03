# One-time setup: write GitHub Actions secrets for production deploy.
# Prerequisites:
#   1. gh auth login   (run once in this terminal)
#   2. Oracle VM running with repo cloned
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts/setup-github-secrets.ps1

$ErrorActionPreference = 'Stop'

function Require-GhAuth {
    gh auth status *> $null
    if ($LASTEXITCODE -ne 0) {
        Write-Host ''
        Write-Host 'Not logged in. Run this first:' -ForegroundColor Yellow
        Write-Host '  gh auth login' -ForegroundColor Cyan
        Write-Host '  (GitHub.com -> HTTPS -> Login with browser -> authorize)' -ForegroundColor Gray
        exit 1
    }
}

Require-GhAuth

$repo = gh repo view --json nameWithOwner -q .nameWithOwner
Write-Host "Repository: $repo" -ForegroundColor Green
Write-Host ''

$host_    = Read-Host 'PROD_SSH_HOST (VM IP or duckdns domain)'
$user     = Read-Host 'PROD_SSH_USER [ubuntu]'
if ([string]::IsNullOrWhiteSpace($user)) { $user = 'ubuntu' }
$appDir   = Read-Host 'PROD_APP_DIR [/home/ubuntu/quote-manage-system]'
if ([string]::IsNullOrWhiteSpace($appDir)) { $appDir = '/home/ubuntu/quote-manage-system' }

Write-Host ''
Write-Host 'SSH private key — paste path to your .pem / .key file:' -ForegroundColor Cyan
$keyPath = Read-Host 'Key file path'
if (-not (Test-Path $keyPath)) {
    Write-Error "File not found: $keyPath"
}
$key = Get-Content -Raw -Path $keyPath

Write-Host ''
Write-Host 'Will set these secrets:' -ForegroundColor Yellow
Write-Host "  PROD_SSH_HOST = $host_"
Write-Host "  PROD_SSH_USER = $user"
Write-Host "  PROD_APP_DIR  = $appDir"
Write-Host '  PROD_SSH_KEY  = (private key contents)'
$confirm = Read-Host 'Continue? [y/N]'
if ($confirm -notmatch '^[yY]') { exit 0 }

gh secret set PROD_SSH_HOST --body $host_
gh secret set PROD_SSH_USER --body $user
gh secret set PROD_APP_DIR  --body $appDir
gh secret set PROD_SSH_KEY  --body $key

Write-Host ''
Write-Host 'Done. Verify at:' -ForegroundColor Green
Write-Host "  https://github.com/$repo/settings/secrets/actions"
Write-Host ''
Write-Host 'Next: push to main -> GitHub Actions deploys automatically.' -ForegroundColor Cyan
