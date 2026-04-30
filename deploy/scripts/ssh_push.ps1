param([string]$Token="", [string]$User="tasayur", [string]$Repo="buildee_app")
$env:PATH += ";C:\Program Files\Git\cmd;C:\Program Files\Git\bin;C:\Program Files\Git\usr\bin"
$sshKey  = "$env:USERPROFILE\.ssh\github_buildee"
Set-Location "C:\Users\tasayur\Desktop\buildee_app"

# SSH config
$sshConfig = "$env:USERPROFILE\.ssh\config"
$entry = "`nHost github.com`n  HostName github.com`n  User git`n  IdentityFile $sshKey`n  IdentitiesOnly yes`n  StrictHostKeyChecking no`n"
$existing = if (Test-Path $sshConfig) { Get-Content $sshConfig -Raw } else { "" }
if ($existing -notmatch "github_buildee") {
    Add-Content $sshConfig $entry -Encoding ASCII
    Write-Host "SSH config updated" -ForegroundColor Green
}

# ---- Step 1: SSH connection test ----
Write-Host "`n[1/4] SSH接続テスト..." -ForegroundColor Yellow
$env:GIT_SSH_COMMAND = "ssh -i `"$sshKey`" -o StrictHostKeyChecking=no"
$sshOut = & "C:\Program Files\Git\usr\bin\ssh.exe" -T -i $sshKey -o StrictHostKeyChecking=no git@github.com 2>&1
Write-Host $sshOut
if ($sshOut -match "successfully authenticated|Hi $User") {
    Write-Host "  SSH OK: authenticated as $User" -ForegroundColor Green
} else {
    Write-Host "  SSH may have issues, attempting push anyway..." -ForegroundColor Yellow
}

# ---- Step 2: Create repo via API (if token provided) ----
if ($Token -ne "") {
    Write-Host "`n[2/4] リポジトリ作成..." -ForegroundColor Yellow
    $curlPath = "C:\Windows\System32\curl.exe"
    $jsonBody = "{`"name`":`"$Repo`",`"private`":true,`"auto_init`":false}"
    $apiOut = & $curlPath -s -w "`n%{http_code}" `
        -X POST "https://api.github.com/user/repos" `
        -H "Authorization: Bearer $Token" `
        -H "Accept: application/vnd.github+json" `
        -H "Content-Type: application/json" `
        -d $jsonBody
    $lines  = $apiOut -split "`n"
    $status = $lines[-1].Trim()
    Write-Host ("  API status: " + $status)
    if ($status -eq "201") {
        Write-Host "  Repository created!" -ForegroundColor Green
    } elseif ($status -eq "422") {
        Write-Host "  Repository already exists" -ForegroundColor Yellow
    } else {
        Write-Host "  API failed - repo must be created manually" -ForegroundColor Red
        Write-Host ("  Response: " + ($lines[0..($lines.Count-2)] -join ""))
    }
} else {
    Write-Host "`n[2/4] Token not provided, skipping API repo creation" -ForegroundColor Yellow
}

# ---- Step 3: Set SSH remote ----
Write-Host "`n[3/4] SSHリモート設定..." -ForegroundColor Yellow
$remoteList = git remote 2>&1
if ($remoteList -match "origin") { git remote remove origin 2>&1 | Out-Null }
git remote add origin "git@github.com:$User/$Repo.git"
Write-Host ("  Remote: git@github.com:$User/$Repo.git") -ForegroundColor Green

# ---- Step 4: Push ----
Write-Host "`n[4/4] プッシュ..." -ForegroundColor Yellow
$env:GIT_SSH_COMMAND = "ssh -i `"$sshKey`" -o StrictHostKeyChecking=no -o UserKnownHostsFile=NUL"
$pushOut = git push -u origin main 2>&1
Write-Host $pushOut
if ($LASTEXITCODE -eq 0) {
    Write-Host "`n✅ プッシュ成功!" -ForegroundColor Green
    Write-Host ("  https://github.com/$User/$Repo") -ForegroundColor Cyan
} else {
    Write-Host "`n❌ プッシュ失敗 (exit: $LASTEXITCODE)" -ForegroundColor Red
}
