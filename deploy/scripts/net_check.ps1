Write-Host "--- Network check ---"
try {
    $r = Invoke-WebRequest -Uri 'https://api.github.com' -UseBasicParsing -TimeoutSec 10
    Write-Host ("GitHub API HTTP: " + [int]$r.StatusCode)
} catch {
    Write-Host ("GitHub unreachable: " + $_.Exception.Message)
}

Write-Host "--- curl test ---"
$curlPath = "C:\Windows\System32\curl.exe"
if (Test-Path $curlPath) {
    & $curlPath -s -o NUL -w "%{http_code}" https://api.github.com
    Write-Host ""
} else {
    Write-Host "curl not found"
}

Write-Host "--- git credential helper ---"
$env:PATH += ";C:\Program Files\Git\cmd;C:\Program Files\Git\bin"
git config --global credential.helper
