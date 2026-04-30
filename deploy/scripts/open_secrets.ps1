# GitHub Actions Secrets 設定アシスタント
# 使い方: powershell -ExecutionPolicy Bypass -File .\deploy\scripts\open_secrets.ps1

$repo    = "tasayur/buildee_app"
$keyFile = "$env:USERPROFILE\.ssh\buildee_deploy"

Write-Host ""
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host "  GitHub Actions Secrets 設定アシスタント" -ForegroundColor Cyan
Write-Host "=================================================" -ForegroundColor Cyan
Write-Host ""

# --- サーバーIP入力 ---
$serverIP = Read-Host "本番サーバーのIPアドレスを入力 (例: 203.0.113.10)"
if (-not $serverIP) { $serverIP = "（未設定）" }

# --- 秘密鍵読み込み ---
if (Test-Path $keyFile) {
    $privKey = (Get-Content $keyFile -Raw).Trim()
    Write-Host ""
    Write-Host "✅ 秘密鍵ファイル確認: $keyFile" -ForegroundColor Green
} else {
    Write-Host "[ERROR] 秘密鍵が見つかりません: $keyFile" -ForegroundColor Red
    Write-Host "先に gen_deploy_key.bat を実行してください。"
    exit 1
}

# --- 表示 ---
Write-Host ""
Write-Host "=================================================" -ForegroundColor Yellow
Write-Host "  以下の4つを GitHub Secrets に登録してください" -ForegroundColor Yellow
Write-Host "=================================================" -ForegroundColor Yellow
Write-Host ""
Write-Host "  1. PROD_HOST    = $serverIP" -ForegroundColor White
Write-Host "  2. PROD_USER    = buildee" -ForegroundColor White
Write-Host "  3. PROD_SSH_KEY = (次のステップでコピー)" -ForegroundColor White
Write-Host "  4. PROD_APP_DIR = /opt/buildee_app" -ForegroundColor White
Write-Host ""

# --- ブラウザ起動 ---
Write-Host "ブラウザで GitHub Secrets ページを開きます..." -ForegroundColor Cyan
Start-Process "https://github.com/$repo/settings/secrets/actions"
Start-Sleep -Seconds 2

# --- 1つずつ順番にコピー ---
$secrets = @(
    @{ Name="PROD_HOST";    Value=$serverIP        },
    @{ Name="PROD_USER";    Value="buildee"         },
    @{ Name="PROD_SSH_KEY"; Value=$privKey          },
    @{ Name="PROD_APP_DIR"; Value="/opt/buildee_app"}
)

foreach ($s in $secrets) {
    Write-Host ""
    Write-Host "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━" -ForegroundColor Cyan
    Write-Host "  Secret名: $($s.Name)" -ForegroundColor Yellow
    if ($s.Name -ne "PROD_SSH_KEY") {
        Write-Host "  値:       $($s.Value)" -ForegroundColor White
    } else {
        Write-Host "  値:       (秘密鍵 - -----BEGIN から -----END まで)" -ForegroundColor White
    }
    $s.Value | Set-Clipboard
    Write-Host "  ✅ クリップボードにコピーしました" -ForegroundColor Green
    Write-Host ""
    Write-Host "  GitHub の画面で:"
    Write-Host "    [New repository secret] → Name: $($s.Name) → Value: 貼り付け → [Add secret]"
    Read-Host "  完了したら Enter キーを押してください"
}

Write-Host ""
Write-Host "=================================================" -ForegroundColor Green
Write-Host "  ✅ 全 Secrets の設定完了!" -ForegroundColor Green
Write-Host "=================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  確認URL:"
Write-Host "  https://github.com/$repo/settings/secrets/actions" -ForegroundColor Cyan
Write-Host ""
Write-Host "  次のステップ: サーバーのセットアップ"
Write-Host "  full_server_setup.sh を本番サーバーで実行してください"
Write-Host ""
