#!/bin/bash
# ==============================================================
#  nginx/setup_linux.sh  --  BuildeeMgr Linux セットアップ
#  対象: Ubuntu 22.04 / Debian 12
#  実行: sudo bash setup_linux.sh
# ==============================================================
set -euo pipefail

APP_DIR="/opt/buildee_app"
APP_USER="buildee"
NGINX_SITE="/etc/nginx/conf.d/buildee.conf"
SERVICE_FILE="/etc/systemd/system/buildee.service"

echo "======================================"
echo " BuildeeMgr Linux セットアップ"
echo "======================================"

# ---- 1. 依存パッケージ ----
echo "[1/7] パッケージのインストール..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nginx certbot python3-certbot-nginx

# ---- 2. アプリユーザー作成 ----
echo "[2/7] アプリユーザーの作成..."
id -u "$APP_USER" &>/dev/null || useradd -r -s /bin/false "$APP_USER"

# ---- 3. アプリ配置 ----
echo "[3/7] アプリファイルの配置..."
mkdir -p "$APP_DIR"
cp -r ./* "$APP_DIR/"
chown -R "$APP_USER:$APP_USER" "$APP_DIR"

# ---- 4. Python 仮想環境 ----
echo "[4/7] Python 仮想環境の構築..."
python3 -m venv "$APP_DIR/.venv"
"$APP_DIR/.venv/bin/pip" install --quiet -r "$APP_DIR/requirements.txt" gunicorn

# ---- 5. TLS 証明書 (自己署名) ----
echo "[5/7] TLS 証明書の生成..."
mkdir -p "$APP_DIR/certs"
"$APP_DIR/.venv/bin/python" "$APP_DIR/cert_utils.py" 2>/dev/null || \
    python3 -c "import sys; sys.path.insert(0,'$APP_DIR'); import cert_utils; cert_utils.generate_self_signed()"

# Nginx用にコピー
mkdir -p /etc/nginx/ssl
cp "$APP_DIR/certs/buildee.crt" /etc/nginx/ssl/
cp "$APP_DIR/certs/buildee.key" /etc/nginx/ssl/
chmod 600 /etc/nginx/ssl/buildee.key
chown root:root /etc/nginx/ssl/buildee.key

# ---- 6. Nginx 設定 ----
echo "[6/7] Nginx の設定..."
cp "$APP_DIR/nginx/nginx.conf"           /etc/nginx/nginx.conf
cp "$APP_DIR/nginx/conf.d/buildee.conf"  "$NGINX_SITE"
cp "$APP_DIR/nginx/conf.d/proxy_params.conf" /etc/nginx/conf.d/proxy_params.conf

# /app/static → APP_DIR/static にシンボリックリンク (Docker設定との互換)
ln -sfn "$APP_DIR/static" /app/static 2>/dev/null || true

nginx -t && systemctl reload nginx
echo "   Nginx 設定 OK"

# ---- 7. systemd サービス ----
echo "[7/7] systemd サービスの登録..."
cat > "$SERVICE_FILE" <<EOF
[Unit]
Description=BuildeeMgr 施工管理システム (Gunicorn)
After=network.target

[Service]
Type=notify
User=$APP_USER
WorkingDirectory=$APP_DIR
Environment="PATH=$APP_DIR/.venv/bin"
ExecStart=$APP_DIR/.venv/bin/gunicorn -c $APP_DIR/gunicorn.conf.py wsgi:app
ExecReload=/bin/kill -s HUP \$MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable buildee
systemctl restart buildee

echo ""
echo "======================================"
echo " セットアップ完了!"
echo "======================================"
echo " アクセス先: https://$(hostname -I | awk '{print $1}')"
echo ""
echo " サービス確認: systemctl status buildee"
echo " Nginx ログ:   tail -f /var/log/nginx/buildee_access.log"
echo " アプリログ:   journalctl -u buildee -f"
echo ""
echo " 本番ドメイン設定後:"
echo "   certbot --nginx -d yourdomain.com"
echo "======================================"
