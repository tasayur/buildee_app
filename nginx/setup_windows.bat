@echo off
chcp 65001 > nul
echo ======================================
echo  BuildeeMgr Nginx Windows セットアップ
echo ======================================
echo.

set NGINX_DIR=C:\nginx
set APP_DIR=%~dp0..
set CERT_SRC=%APP_DIR%certs

:: Nginx の存在確認
if not exist "%NGINX_DIR%\nginx.exe" (
    echo [ERROR] Nginx が見つかりません。
    echo.
    echo  以下の手順でインストールしてください:
    echo  1. https://nginx.org/en/download.html を開く
    echo  2. nginx/Windows の最新安定版をダウンロード
    echo  3. C:\nginx\ に展開する
    echo.
    pause
    exit /b 1
)

echo [1/4] Nginx バージョン確認...
"%NGINX_DIR%\nginx.exe" -v

echo.
echo [2/4] 設定ファイルをコピー中...
copy /Y "%APP_DIR%nginx\nginx_windows.conf" "%NGINX_DIR%\conf\nginx.conf"

echo.
echo [3/4] SSL証明書をコピー中...
if not exist "%NGINX_DIR%\ssl" mkdir "%NGINX_DIR%\ssl"

if exist "%CERT_SRC%\buildee.crt" (
    copy /Y "%CERT_SRC%\buildee.crt" "%NGINX_DIR%\ssl\buildee.crt"
    copy /Y "%CERT_SRC%\buildee.key" "%NGINX_DIR%\ssl\buildee.key"
    echo    証明書のコピー完了
) else (
    echo [警告] 証明書が見つかりません。先に BuildeeMgr を起動して証明書を生成してください。
    echo         証明書生成後に再実行: %APP_DIR%nginx\setup_windows.bat
    pause
    exit /b 1
)

echo.
echo [4/4] Nginx の設定テスト...
"%NGINX_DIR%\nginx.exe" -t -c "%NGINX_DIR%\conf\nginx.conf"
if errorlevel 1 (
    echo [ERROR] Nginx 設定にエラーがあります。nginx.conf を確認してください。
    pause
    exit /b 1
)

echo.
echo ======================================
echo  セットアップ完了!
echo ======================================
echo.
echo  次の手順:
echo  1. BuildeeMgr を起動 (start.bat)
echo     ※ app.py のポートを 5000 のまま使用
echo.
echo  2. Nginx を起動:
echo     %NGINX_DIR%\nginx.exe
echo.
echo  3. ブラウザで https://localhost を開く
echo.
echo  Nginx の操作:
echo    起動:   %NGINX_DIR%\nginx.exe
echo    停止:   %NGINX_DIR%\nginx.exe -s stop
echo    再読込: %NGINX_DIR%\nginx.exe -s reload
echo    確認:   tasklist /fi "imagename eq nginx.exe"
echo.
pause
