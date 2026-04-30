#!/bin/bash
# ================================================================
#  deploy/scripts/server_setup.sh
#  Ubuntu 22.04 / Debian 12 への初回サーバーセットアップ
#  実行: sudo bash deploy/scripts/server_setup.sh
# ================================================================
set -euo pipefail

APP_USER="buildee"
APP_DIR="/opt/buildee_app"
DOCKER_COMPOSE_VERSION="2.27.0"

echo "========================================"
echo "  BuildeeMgr サーバー初期セットアップ"
echo "========================================"

# ---- 1. システム更新 ----
echo "[1/7] システム更新..."
apt-get update -qq
apt-get upgrade -y -qq

# ---- 2. 必須パッケージ ----
echo "[2/7] 必須パッケージのインストール..."
apt-get install -y -qq \
    curl git ufw fail2ban \
    ca-certificates gnupg lsb-release

# ---- 3. Docker インストール ----
echo "[3/7] Docker のインストール..."
if ! command -v docker &>/dev/null; then
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable docker
    systemctl start docker
    echo "   Docker インストール完了: $(docker --version)"
else
    echo "   Docker 既存: $(docker --version)"
fi

# ---- 4. アプリユーザー作成 ----
echo "[4/7] アプリユーザーの作成..."
id -u "$APP_USER" &>/dev/null || useradd -m -s /bin/bash "$APP_USER"
usermod -aG docker "$APP_USER"

# ---- 5. アプリディレクトリ ----
echo "[5/7] アプリディレクトリの準備..."
mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

# ---- 6. ファイアウォール設定 ----
echo "[6/7] UFW ファイアウォール設定..."
ufw --force reset
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
echo "   UFW: $(ufw status | head -1)"

# ---- 7. Fail2ban (SSH ブルートフォース対策) ----
echo "[7/7] Fail2ban の設定..."
cat > /etc/fail2ban/jail.local <<'EOF'
[sshd]
enabled  = true
port     = ssh
maxretry = 5
bantime  = 3600
findtime = 600

[nginx-http-auth]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/buildee_error.log
maxretry = 5
bantime  = 3600
EOF
systemctl enable fail2ban
systemctl restart fail2ban

echo ""
echo "========================================"
echo "  セットアップ完了!"
echo "========================================"
echo ""
echo "  次の手順:"
echo "  1. アプリコードを $APP_DIR に配置"
echo "  2. cp deploy/env.prod.example .env && vim .env"
echo "  3. bash deploy/scripts/deploy.sh"
echo ""
echo "  SSH再ログイン後にdockerコマンドが使えるようになります"
echo "========================================"
