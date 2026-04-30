@echo off
chcp 65001 > nul
echo === BuildeeMgr 本番デプロイ用 SSH キー生成 ===
echo.

set KEYFILE=%USERPROFILE%\.ssh\buildee_deploy

if exist "%KEYFILE%" (
    echo 既存キーを削除して再生成します...
    del /f "%KEYFILE%" "%KEYFILE%.pub" 2>nul
)

echo. | "C:\Program Files\Git\usr\bin\ssh-keygen.exe" -t ed25519 -C "buildee-deploy@github-actions" -f "%KEYFILE%" -q
ping -n 2 127.0.0.1 > nul

if not exist "%KEYFILE%.pub" (
    echo [ERROR] キー生成に失敗しました
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  [GitHub Secrets に登録] PROD_SSH_KEY の値:
echo  (秘密鍵 - GitHub Secrets へ貼り付け)
echo ============================================================
type "%KEYFILE%"

echo.
echo ============================================================
echo  [サーバーに登録] authorized_keys に追加する公開鍵:
echo ============================================================
type "%KEYFILE%.pub"

echo.
echo ============================================================
echo  公開鍵をクリップボードにコピーしました
echo  → サーバーの ~/.ssh/authorized_keys に貼り付けてください
echo ============================================================
type "%KEYFILE%.pub" | clip

echo.
echo 秘密鍵の場所: %KEYFILE%
echo 公開鍵の場所: %KEYFILE%.pub
echo.
pause
