@echo off
chcp 65001 > nul
echo ===================================
echo   BuildeeMgr 施工管理システム
echo ===================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python が見つかりません。Python 3.8 以上をインストールしてください。
    pause & exit /b
)

echo [1/3] 依存パッケージを確認中...
pip install flask flask-login bcrypt openpyxl pillow "qrcode[pil]" pyopenssl cryptography --quiet 2>nul

echo [2/3] データベースを準備中...
python migrate.py

echo [3/3] アプリを起動中...
echo.
echo  HTTPS: https://localhost:5443
echo  HTTP : http://localhost:5000  (HTTPS へリダイレクト)
echo  初期ログイン: admin / admin1234
echo.
echo  ブラウザの「接続の安全性」警告が出た場合は「詳細設定」から続行してください
echo  (自己署名証明書のため — 本番では正式な証明書を使用してください)
echo.
echo  終了するには Ctrl+C を押してください
echo.
start "" "https://localhost:5443"
python app.py
pause
