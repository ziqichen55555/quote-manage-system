param([string]$File, [string]$StartMatch = '')
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$h = [System.IO.File]::ReadAllText("$env:TEMP\$File")
$body = $h `
    -replace '(?s)<script[^>]*>.*?</script>',' ' `
    -replace '(?s)<style[^>]*>.*?</style>',' ' `
    -replace '<[^>]+>',"`n" `
    -replace '&nbsp;',' ' `
    -replace '&amp;','&' `
    -replace '&#x27;',"'" `
    -replace '&#39;',"'"
$seen = [System.Collections.Generic.HashSet[string]]::new()
$out = New-Object System.Collections.ArrayList
foreach ($line in ($body -split "`n")) {
    $t = $line.Trim()
    if ($t.Length -lt 2 -or $t.Length -gt 400) { continue }
    if ($t -match '^[0-9{};:#\.\-\s]+$') { continue }
    if ($t -match '^--') { continue }
    if ($seen.Add($t)) { [void]$out.Add($t) }
}
$start = 0
if ($StartMatch) {
    for ($i = 0; $i -lt $out.Count; $i++) {
        if ($out[$i] -like "*$StartMatch*") { $start = $i; break }
    }
}
$end = [Math]::Min($out.Count - 1, $start + 120)
$out[$start..$end] -join "`n"
