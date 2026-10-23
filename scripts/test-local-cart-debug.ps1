# Quick check: cart debug routes on local Odoo (8069 / 8070).
$ErrorActionPreference = "Stop"
$urls = @(
    "http://localhost:8069/shop/cart/debug",
    "http://localhost:8069/quote-cart-debug",
    "http://localhost:8070/shop/cart/debug"
)
foreach ($u in $urls) {
    try {
        $r = Invoke-WebRequest -Uri $u -UseBasicParsing -TimeoutSec 15
        $preview = ($r.Content -replace "\s+", " ").Substring(0, [Math]::Min(120, $r.Content.Length))
        Write-Host ("OK {0} -> {1}" -f $r.StatusCode, $u) -ForegroundColor Green
        Write-Host "     $preview..."
    } catch {
        $code = $_.Exception.Response.StatusCode.value__
        Write-Host ("FAIL {0} -> {1}" -f $code, $u) -ForegroundColor Red
    }
}
Write-Host ""
Write-Host "Enable: Settings > System Parameter quote_manage_ui.website_cart_debug = 1"
Write-Host "Then: docker compose restart web"
Write-Host "Guest test: incognito /shop -> add to cart -> /shop/cart (debug box at top)"
