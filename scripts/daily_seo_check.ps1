# Daily public SEO / site health checks for Re-Ware (no production SSH).
# Usage:
#   .\scripts\daily_seo_check.ps1
#   .\scripts\daily_seo_check.ps1 -BaseUrl "https://www.reware-project.com"
param(
    [string]$BaseUrl = "https://www.reware-project.com",
    [int]$SitemapSampleSize = 5
)

$ErrorActionPreference = "Stop"

function Write-Issue([string]$Level, [string]$Message) {
    $color = switch ($Level) {
        "FAIL" { "Red" }
        "WARN" { "Yellow" }
        default { "White" }
    }
    Write-Host "[$Level] $Message" -ForegroundColor $color
}

function Get-PageMeta([string]$Html) {
    $title = $null
    if ($Html -match '<title>([^<]+)</title>') { $title = $Matches[1].Trim() }

    $description = $null
    if ($Html -match '<meta[^>]+name\s*=\s*"description"[^>]+content\s*=\s*"([^"]*)"') {
        $description = $Matches[1].Trim()
    } elseif ($Html -match '<meta[^>]+content\s*=\s*"([^"]*)"[^>]+name\s*=\s*"description"') {
        $description = $Matches[1].Trim()
    }

    $canonical = $null
    if ($Html -match '<link[^>]+rel\s*=\s*"canonical"[^>]+href\s*=\s*"([^"]*)"') {
        $canonical = $Matches[1].Trim()
    } elseif ($Html -match '<link[^>]+href\s*=\s*"([^"]*)"[^>]+rel\s*=\s*"canonical"') {
        $canonical = $Matches[1].Trim()
    }

    $robots = $null
    if ($Html -match '<meta[^>]+name\s*=\s*"robots"[^>]+content\s*=\s*"([^"]*)"') {
        $robots = $Matches[1].Trim()
    }

    [PSCustomObject]@{
        Title       = $title
        Description = $description
        Canonical   = $canonical
        Robots      = $robots
    }
}

$BaseUrl = $BaseUrl.TrimEnd("/")
$fail = 0
$warn = 0
$stamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"

Write-Host ""
Write-Host "=== Daily SEO check ($stamp) ===" -ForegroundColor Cyan
Write-Host "Base: $BaseUrl"
Write-Host ""

$paths = @(
    "/",
    "/shop",
    "/robots.txt",
    "/sitemap.xml"
)

foreach ($path in $paths) {
    $url = "$BaseUrl$path"
    try {
        if ($path -eq "/robots.txt" -or $path -eq "/sitemap.xml") {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 60
        } else {
            $resp = Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 60
        }
        if ($resp.StatusCode -ne 200) {
            Write-Issue "FAIL" "$path HTTP $($resp.StatusCode)"
            $fail++
            continue
        }
        Write-Host "[OK] $path -> 200"
    } catch {
        Write-Issue "FAIL" "$path unreachable: $($_.Exception.Message)"
        $fail++
        continue
    }

    if ($path -eq "/robots.txt") {
        $body = $resp.Content
        if ($body -notmatch "(?m)^Sitemap:\s*") {
            Write-Issue "WARN" "robots.txt has no Sitemap: line"
            $warn++
        }
        if ($body -match "(?m)^Disallow:\s*/\s*$") {
            Write-Issue "FAIL" "robots.txt disallows entire site (Disallow: /)"
            $fail++
        }
    }

    if ($path -eq "/sitemap.xml") {
        $locs = @(
            [regex]::Matches($resp.Content, "<loc>\s*(https?://[^<]+)\s*</loc>") |
                ForEach-Object { $_.Groups[1].Value.Trim() }
        )
        if ($locs.Count -lt 1) {
            Write-Issue "FAIL" "sitemap.xml contains no URLs"
            $fail++
        } else {
            Write-Host "     sitemap URLs: $($locs.Count)"
            $sample = $locs | Select-Object -First $SitemapSampleSize
            foreach ($loc in $sample) {
                try {
                    $h = Invoke-WebRequest -Uri $loc -Method Head -UseBasicParsing -TimeoutSec 45
                    if ($h.StatusCode -ge 400) {
                        Write-Issue "WARN" "sitemap URL HTTP $($h.StatusCode): $loc"
                        $warn++
                    }
                } catch {
                    Write-Issue "WARN" "sitemap URL failed: $loc"
                    $warn++
                }
            }
        }
    }

    if ($path -in @("/", "/shop")) {
        $meta = Get-PageMeta $resp.Content
        Write-Host "     title: $($meta.Title)"
        if (-not $meta.Title) {
            Write-Issue "WARN" "$path missing <title>"
            $warn++
        }
        if (-not $meta.Description) {
            Write-Issue "WARN" "$path missing meta description"
            $warn++
        } elseif ($meta.Description -match "homepage of the website") {
            Write-Issue "WARN" "$path still uses placeholder meta description"
            $warn++
        }
        if ($meta.Robots -match "noindex") {
            Write-Issue "FAIL" "$path has robots noindex ($($meta.Robots))"
            $fail++
        }
        if ($meta.Canonical -and ($meta.Canonical -notlike "$BaseUrl*")) {
            Write-Issue "WARN" "$path canonical off-domain: $($meta.Canonical)"
            $warn++
        }
    }
}

Write-Host ""
if ($fail -gt 0) {
    Write-Host "Result: $fail failure(s), $warn warning(s)" -ForegroundColor Red
    exit 1
}
if ($warn -gt 0) {
    Write-Host "Result: OK with $warn warning(s)" -ForegroundColor Yellow
    exit 0
}
Write-Host "Result: all checks passed" -ForegroundColor Green
exit 0
