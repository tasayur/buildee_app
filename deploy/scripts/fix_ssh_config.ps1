$sshDir    = "$env:USERPROFILE\.ssh"
$sshConfig = "$sshDir\config"
$sshKey    = "$sshDir\github_buildee"

Write-Host "=== Fix SSH config (remove BOM, rebuild) ===" -ForegroundColor Cyan

# Read existing config as bytes and strip BOM
if (Test-Path $sshConfig) {
    $bytes = [System.IO.File]::ReadAllBytes($sshConfig)
    # Remove UTF-8 BOM (EF BB BF)
    if ($bytes.Length -ge 3 -and $bytes[0] -eq 0xEF -and $bytes[1] -eq 0xBB -and $bytes[2] -eq 0xBF) {
        $bytes = $bytes[3..($bytes.Length-1)]
        Write-Host "  BOM removed from config" -ForegroundColor Yellow
    }
    $existing = [System.Text.Encoding]::ASCII.GetString($bytes)
    # Remove any previous github_buildee entry
    $lines = $existing -split "`n" | Where-Object { $_ -notmatch "github_buildee|StrictHostKeyChecking" }
    $cleaned = ($lines -join "`n").TrimEnd()
} else {
    $cleaned = ""
}

# Build new config entry (pure ASCII, no BOM)
$newEntry = @"

Host github.com
  HostName github.com
  User git
  IdentityFile $sshKey
  IdentitiesOnly yes
  StrictHostKeyChecking no
"@

$finalConfig = $cleaned + $newEntry
[System.IO.File]::WriteAllText($sshConfig, $finalConfig, [System.Text.Encoding]::ASCII)
Write-Host ("  Config written: " + $sshConfig) -ForegroundColor Green
Write-Host "  Preview:"
Get-Content $sshConfig | ForEach-Object { Write-Host ("    " + $_) }

# Test SSH
Write-Host "`n=== SSH test ===" -ForegroundColor Cyan
$sshExe = "C:\Program Files\Git\usr\bin\ssh.exe"
$out = & $sshExe -T -i $sshKey -F $sshConfig -o StrictHostKeyChecking=no git@github.com 2>&1
Write-Host $out
if ($out -match "successfully authenticated|Hi ") {
    Write-Host "SSH OK!" -ForegroundColor Green
} else {
    Write-Host "SSH test result above (exit expected)" -ForegroundColor Yellow
}
