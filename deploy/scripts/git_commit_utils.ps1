$env:PATH += ";C:\Program Files\Git\cmd;C:\Program Files\Git\bin"
Set-Location "C:\Users\tasayur\Desktop\buildee_app"
git add -A
git commit -m "chore: add git utility scripts"
git log --oneline
