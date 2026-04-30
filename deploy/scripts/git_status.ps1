$env:PATH += ";C:\Program Files\Git\cmd;C:\Program Files\Git\bin"
Set-Location "C:\Users\tasayur\Desktop\buildee_app"
Write-Host "=== git log ===" -ForegroundColor Cyan
git log --oneline
Write-Host ""
Write-Host "=== git status ===" -ForegroundColor Cyan
git status
Write-Host ""
$count = (git ls-files).Count
Write-Host ("Total tracked files: " + $count) -ForegroundColor Green
