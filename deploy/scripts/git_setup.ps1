$ErrorActionPreference = "Stop"
$env:PATH = $env:PATH + ";C:\Program Files\Git\cmd;C:\Program Files\Git\bin"
Set-Location "C:\Users\tasayur\Desktop\buildee_app"

Write-Host "=== Git セットアップ ===" -ForegroundColor Cyan
Write-Host ("Git version: " + (git --version))

# .gitignore 更新
$gi = Get-Content ".gitignore" -Raw -Encoding UTF8
$add = ""
if ($gi -notmatch "_scan") { $add += "`n_scan.py`n_*.py`n*.backup" }
if ($gi -notmatch "^backups") { $add += "`nbackups/" }
if ($add) {
    Add-Content ".gitignore" $add -Encoding UTF8
    Write-Host ("Updated .gitignore: " + $add.Trim())
}

# ステージング
git add -A
$staged = (git diff --cached --name-only) -split "`n" | Where-Object { $_ -ne "" }
Write-Host ("Staged: " + $staged.Count + " files")
$staged | ForEach-Object { Write-Host ("  + " + $_) }

# コミット
$msg = @"
feat: BuildeeMgr v1.0.0 -- 施工管理システム

実装済み機能:
- 調整会議 / 電子KY / 労務安全 / 入退場管理
- PWA対応 (Service Worker / オフライン)
- ログイン認証 (flask-login + bcrypt / 3段階RBAC)
- HTTPS/TLS (自己署名 + Let's Encrypt自動更新)
- Nginx リバースプロキシ + レート制限
- メール通知 (SMTP: Gmail/Outlook/SendGrid対応)
- バックアップ自動化 (日次/週次/月次 + SHA-256検証)
- Docker化 + docker-compose 本番構成
- GitHub Actions CI/CD パイプライン
- Excel出力 / QRコード入退場
"@

git commit -m $msg
Write-Host "Commit OK" -ForegroundColor Green
git log --oneline -3
