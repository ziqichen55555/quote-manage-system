
# List recent GitHub Actions runs and block if production jobs are active.
# Usage: .\scripts\check-prod-jobs.ps1
# Exit 0 = no matching active jobs found.
# Exit 1 = active job found or unable to verify safely.

$ErrorActionPreference = "Stop"

function ConvertFrom-GhJsonArray {
    param([AllowNull()][string]$Raw)

    if ([string]::IsNullOrWhiteSpace($Raw)) {
        return @()
    }

    $parsed = ConvertFrom-Json -InputObject $Raw

    if ($null -eq $parsed) {
        return @()
    }

    if ($parsed -is [System.Array]) {
        return @($parsed)
    }

    return @($parsed)
}

Write-Host "Checking GitHub Actions production jobs..." -ForegroundColor Cyan

# Query GitHub Actions. Do not merge stderr into JSON.
$listRaw = gh run list --limit 100 --json status,name,databaseId,url,createdAt

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERROR: GitHub Actions query failed. Do not deploy." -ForegroundColor Red
    exit 1
}

try {
    $allRuns = @(ConvertFrom-GhJsonArray ($listRaw | Out-String))
}
catch {
    Write-Host "ERROR: Unable to parse GitHub Actions JSON. Do not deploy." -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Yellow
    exit 1
}

$activeStatuses = @("queued", "in_progress", "pending", "waiting")

$blocking = @(
    $allRuns | Where-Object {
        $_.status -in $activeStatuses -and
        $_.name -match "Deploy production|Repair production|Run Odoo shell"
    }
)

Write-Host ""

if ($blocking.Count -gt 0) {
    Write-Host "NOT SAFE - production job in progress:" -ForegroundColor Red

    $blocking | ForEach-Object {
        Write-Host ("  [{0}] {1}  {2}" -f $_.status, $_.name, $_.url)
    }

    Write-Host ""
    Write-Host "Wait until all matching jobs finish. Do not deploy in parallel." -ForegroundColor Yellow
    exit 1
}

Write-Host "OK - no matching active jobs found in the returned runs." -ForegroundColor Green
Write-Host "Note: this check is not an atomic deployment lock." -ForegroundColor Yellow
exit 0
