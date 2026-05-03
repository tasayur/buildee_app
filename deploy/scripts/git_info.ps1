$env:PATH += ";C:\Program Files\Git\cmd;C:\Program Files\Git\bin"
Set-Location "C:\Users\tasayur\Desktop\buildee_app"
Write-Host "=== git log ===" -ForegroundColor Cyan
git log --oneline
Write-Host "`n=== git remote ===" -ForegroundColor Cyan
git remote -v
Write-Host "`n=== tracked files ===" -ForegroundColor Cyan
Write-Host ((git ls-files).Count.ToString() + " files tracked")
