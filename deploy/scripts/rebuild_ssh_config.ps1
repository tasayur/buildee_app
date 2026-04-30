$sshDir    = "$env:USERPROFILE\.ssh"
$sshKey    = "$sshDir\github_buildee"
$sshConfig = "$sshDir\config"

Write-Host "=== Rebuild SSH config (clean) ===" -ForegroundColor Cyan

# Show current key fingerprint
$sshExe = "C:\Program Files\Git\usr\bin\ssh-keygen.exe"
if (Test-Path "$sshKey.pub") {
    $fp = & $sshExe -l -f "$sshKey.pub" 2>&1
    Write-Host ("Local key fingerprint: " + $fp)
}

# Write clean config (ASCII, no BOM, no duplicates)
$clean = @"
Host github.com
  HostName github.com
  User git
  IdentityFile $sshKey
  IdentitiesOnly yes
  StrictHostKeyChecking no
  UserKnownHostsFile NUL
"@
[System.IO.File]::WriteAllText($sshConfig, $clean.TrimStart(), [System.Text.Encoding]::ASCII)
Write-Host "Config rebuilt:"
Get-Content $sshConfig | ForEach-Object { Write-Host ("  " + $_) }

# SSH test with verbose
Write-Host "`n=== SSH test (verbose) ===" -ForegroundColor Cyan
$sshBin = "C:\Program Files\Git\usr\bin\ssh.exe"
& $sshBin -vvv -T -F $sshConfig -i $sshKey git@github.com 2>&1 | Where-Object {
    $_ -match "Authentications|Trying|key|Accepted|denied|debug1" -and
    $_ -notmatch "debug3|debug2|debug1: (?!auth|send|SSH2_MSG_USERAUTH|server accepts)"
} | Select-Object -First 30
