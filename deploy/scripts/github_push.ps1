# ================================================================
#  deploy\scripts\github_push.ps1
#  BuildeeMgr GitHub プッシュ & 本番展開 準備スクリプト
#
#  実行方法（PowerShell を管理者で開く）:
#    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
#    .\deploy\scripts\github_push.ps1 -GitHubUser "あなたのユーザー名" -RepoName "buildee_app"
#
#  引数:
#    -GitHubUser   GitHub ユーザー名（必須）
#    -RepoName     リポジトリ名（デフォルト: buildee_app）
#    -Branch       ブランチ名（デフォルト: main）
#    -Private      プライベートリポジトリにする（デフォルト: $true）
# ================================================================
param(
    [Parameter(Mandatory=$true)]
    [string]$GitHubUser,

    [string]$RepoName  = "buildee_app",
    [string]$Branch    = "main",
    [bool]  $Private   = $true
)

$ErrorActionPreference = "Stop"
$AppDir = Split-Path (Split-Path $PSScriptRoot -Parent) -Parent
Set-Location $AppDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  BuildeeMgr GitHub プッシュ準備" -ForegroundColor Cyan
Write-Host "  User:   $GitHubUser" -ForegroundColor Cyan
Write-Host "  Repo:   $RepoName" -ForegroundColor Cyan
Write-Host "  Branch: $Branch" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ---- Step 1: Git インストール確認 ----
Write-Host "`n[1/7] Git の確認..." -ForegroundColor Yellow
try {
    $gitVersion = git --version 2>&1
    Write-Host "  ✅ $gitVersion" -ForegroundColor Green
} catch {
    Write-Host "  Git が見つかりません。インストールします..." -ForegroundColor Yellow
    winget install --id Git.Git -e --silent --accept-package-agreements --accept-source-agreements
    $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
    Write-Host "  ✅ Git インストール完了" -ForegroundColor Green
}

# ---- Step 2: Git 初期設定 ----
Write-Host "`n[2/7] Git 初期設定..." -ForegroundColor Yellow
$gitName  = git config --global user.name  2>$null
$gitEmail = git config --global user.email 2>$null

if (-not $gitName) {
    $gitName = Read-Host "  Git ユーザー名を入力してください（例: 山田太郎）"
    git config --global user.name $gitName
}
if (-not $gitEmail) {
    $gitEmail = Read-Host "  Git メールアドレスを入力してください"
    git config --global user.email $gitEmail
}

git config --global core.autocrlf true
git config --global init.defaultBranch main
Write-Host "  ✅ Git 設定: $gitName <$gitEmail>" -ForegroundColor Green

# ---- Step 3: .gitignore 最終確認 ----
Write-Host "`n[3/7] .gitignore 確認..." -ForegroundColor Yellow
$gitignore = Get-Content ".gitignore" -Raw -ErrorAction SilentlyContinue
$required  = @(".env", "certs/", "buildee.db", "backups/", "__pycache__/")
foreach ($item in $required) {
    if ($gitignore -notmatch [regex]::Escape($item)) {
        Add-Content ".gitignore" "`n$item"
        Write-Host "  追加: $item" -ForegroundColor Yellow
    }
}
Write-Host "  ✅ .gitignore OK" -ForegroundColor Green

# ---- Step 4: git init & 初回コミット ----
Write-Host "`n[4/7] Git リポジトリ初期化..." -ForegroundColor Yellow

if (-not (Test-Path ".git")) {
    git init -b $Branch
    Write-Host "  git init 完了" -ForegroundColor Green
} else {
    Write-Host "  既存の .git を使用します" -ForegroundColor Green
}

git add -A
$status = git status --short
$fileCount = ($status | Measure-Object -Line).Lines
Write-Host "  ステージング済み: $fileCount ファイル" -ForegroundColor Green

git commit -m "feat: BuildeeMgr 初回コミット

機能一覧:
- Flask + SQLite バックエンド
- ログイン認証 (flask-login + bcrypt)
- HTTPS / TLS 証明書管理
- Nginx リバースプロキシ設定
- メール通知 (SMTP)
- バックアップ自動化
- Let's Encrypt 自動更新
- Docker 本番デプロイ構成
- GitHub Actions CI/CD" 2>&1 | Write-Host
Write-Host "  ✅ 初回コミット完了" -ForegroundColor Green

# ---- Step 5: GitHub リポジトリ作成 ----
Write-Host "`n[5/7] GitHub リポジトリの作成..." -ForegroundColor Yellow

# GitHub CLI があれば使う
$ghInstalled = $null
try { $ghInstalled = gh --version 2>&1 } catch {}

if ($ghInstalled) {
    Write-Host "  GitHub CLI を使用します" -ForegroundColor Green
    $visibility = if ($Private) { "--private" } else { "--public" }
    gh repo create "$GitHubUser/$RepoName" $visibility --description "BuildeeMgr 施工管理システム" --confirm 2>&1 | Write-Host
    $remoteUrl = "https://github.com/$GitHubUser/$RepoName.git"
} else {
    Write-Host "  GitHub CLI が未インストールです。" -ForegroundColor Yellow
    Write-Host "  以下の手順で手動作成してください:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  1. https://github.com/new を開く" -ForegroundColor White
    Write-Host "  2. Repository name: $RepoName" -ForegroundColor White
    Write-Host "  3. Private を選択" -ForegroundColor White
    Write-Host "  4. 'Create repository' をクリック" -ForegroundColor White
    Write-Host ""
    $remoteUrl = "https://github.com/$GitHubUser/$RepoName.git"
    Read-Host "  作成完了後 Enter を押してください"
}

# ---- Step 6: リモート設定 & プッシュ ----
Write-Host "`n[6/7] GitHub へプッシュ..." -ForegroundColor Yellow

$existingRemote = git remote 2>&1
if ($existingRemote -contains "origin") {
    git remote set-url origin $remoteUrl
} else {
    git remote add origin $remoteUrl
}

Write-Host "  Remote: $remoteUrl" -ForegroundColor Green
Write-Host "  プッシュ中（認証が求められる場合は GitHub ユーザー名とトークンを入力）..."
git push -u origin $Branch 2>&1 | Write-Host
Write-Host "  ✅ プッシュ完了!" -ForegroundColor Green

# ---- Step 7: GitHub Actions Secrets 設定ガイド ----
Write-Host "`n[7/7] GitHub Actions Secrets 設定ガイド..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  リポジトリ: https://github.com/$GitHubUser/$RepoName" -ForegroundColor Cyan
Write-Host "  Settings → Secrets and variables → Actions → New repository secret" -ForegroundColor White
Write-Host ""
Write-Host "  追加が必要な Secrets:" -ForegroundColor Yellow
@(
    @{ Name="PROD_HOST";    Desc="本番サーバーのIPまたはドメイン（例: 203.0.113.1）" },
    @{ Name="PROD_USER";    Desc="SSHユーザー名（例: ubuntu）" },
    @{ Name="PROD_SSH_KEY"; Desc="SSH秘密鍵の内容（-----BEGIN ... KEY-----）" },
    @{ Name="PROD_APP_DIR"; Desc="サーバー上のアプリパス（例: /opt/buildee_app）" }
) | ForEach-Object {
    Write-Host "    $($_.Name.PadRight(16)) — $($_.Desc)" -ForegroundColor White
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  ✅ 完了!" -ForegroundColor Green
Write-Host ""
Write-Host "  リポジトリ: https://github.com/$GitHubUser/$RepoName" -ForegroundColor Cyan
Write-Host "  次の手順: サーバーで sudo bash deploy/scripts/server_setup.sh" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Green
