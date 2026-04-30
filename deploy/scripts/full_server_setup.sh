#!/bin/bash
# ================================================================
#  deploy/scripts/full_server_setup.sh
#  BuildeeMgr 本番サーバー 完全セットアップ（初回1回だけ実行）
#
#  使い方:
#    curl -fsSL https://raw.githubusercontent.com/tasayur/buildee_app/main/deploy/scripts/full_server_setup.sh | sudo bash
#  または:
#    sudo bash deploy/scripts/full_server_setup.sh
#
#  オプション:
#    DEPLOY_PUBKEY="ssh-ed25519 AAAA..."  # GitHub Actions 用公開鍵
#    APP_DOMAIN="example.com"             # ドメイン（Let's Encrypt用）
# ================================================================
set -euo pipefail

APP_USER="${APP_USER:-buildee}"
APP_DIR="${APP_DIR:-/opt/buildee_app}"
DEPLOY_PUBKEY="${DEPLOY_PUBKEY:-ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILlpmCp+a0gyMePLjbRL8BJLO3aWgnqrj7qqZxiP8o/F buildee-deploy@github-actions}"
GITHUB_REPO="${GITHUB_REPO:-https://github.com/tasayur/buildee_app.git}"
APP_DOMAIN="${APP_DOMAIN:-}"

echo "========================================================"
echo "  BuildeeMgr 本番サーバー セットアップ"
echo "  App User:   $APP_USER"
echo "  App Dir:    $APP_DIR"
echo "  Domain:     ${APP_DOMAIN:-（未設定 - IPアクセス）}"
echo "========================================================"

# root チェック
if [ "$(id -u)" -ne 0 ]; then
    echo "[ERROR] root で実行してください: sudo bash $0"
    exit 1
fi

# ---- 1. システム更新 ----
echo ""
echo "[1/9] システム更新..."
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get upgrade -y -qq
apt-get install -y -qq curl git ufw fail2ban ca-certificates gnupg lsb-release htop

# ---- 2. Docker インストール ----
echo ""
echo "[2/9] Docker インストール..."
if command -v docker &>/dev/null; then
    echo "  Docker 既存: $(docker --version)"
else
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update -qq
    apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
    systemctl enable --now docker
    echo "  ✅ Docker: $(docker --version)"
fi

# ---- 3. アプリユーザー作成 ----
echo ""
echo "[3/9] アプリユーザー ($APP_USER) 作成..."
if id "$APP_USER" &>/dev/null; then
    echo "  ユーザー既存"
else
    useradd -m -s /bin/bash "$APP_USER"
    echo "  ユーザー作成完了"
fi
usermod -aG docker "$APP_USER"

# ---- 4. SSH 公開鍵登録（GitHub Actions 用） ----
echo ""
echo "[4/9] GitHub Actions デプロイ用 SSH 公開鍵登録..."
DEPLOY_HOME=$(eval echo "~$APP_USER")
mkdir -p "$DEPLOY_HOME/.ssh"
chmod 700 "$DEPLOY_HOME/.ssh"
touch "$DEPLOY_HOME/.ssh/authorized_keys"

if grep -qF "$DEPLOY_PUBKEY" "$DEPLOY_HOME/.ssh/authorized_keys" 2>/dev/null; then
    echo "  公開鍵は登録済み"
else
    echo "$DEPLOY_PUBKEY" >> "$DEPLOY_HOME/.ssh/authorized_keys"
    echo "  ✅ 公開鍵登録完了"
fi
chmod 600 "$DEPLOY_HOME/.ssh/authorized_keys"
chown -R "$APP_USER:$APP_USER" "$DEPLOY_HOME/.ssh"

# ---- 5. アプリコードのクローン ----
echo ""
echo "[5/9] アプリコード取得..."
mkdir -p "$APP_DIR"
chown "$APP_USER:$APP_USER" "$APP_DIR"

if [ -d "$APP_DIR/.git" ]; then
    echo "  既存リポジトリを更新..."
    sudo -u "$APP_USER" git -C "$APP_DIR" pull origin main
else
    echo "  GitHub からクローン..."
    sudo -u "$APP_USER" git clone "$GITHUB_REPO" "$APP_DIR"
fi
echo "  ✅ コード取得完了"

# ---- 6. .env ファイル作成 ----
echo ""
echo "[6/9] 環境設定ファイル作成..."
if [ -f "$APP_DIR/.env" ]; then
    echo "  .env 既存（スキップ）"
else
    cp "$APP_DIR/deploy/env.prod.example" "$APP_DIR/.env"
    # SECRET_KEY を自動生成
    SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=$SECRET_KEY/" "$APP_DIR/.env"
    # ドメインが指定されていれば設定
    if [ -n "$APP_DOMAIN" ]; then
        sed -i "s/APP_DOMAIN=.*/APP_DOMAIN=$APP_DOMAIN/" "$APP_DIR/.env" 2>/dev/null || true
    fi
    chown "$APP_USER:$APP_USER" "$APP_DIR/.env"
    chmod 600 "$APP_DIR/.env"
    echo "  ✅ .env 作成完了（SECRET_KEY 自動生成済み）"
    echo ""
    echo "  ⚠️  以下の項目を手動で設定してください:"
    echo "     SMTP_USER / SMTP_PASSWORD (メール通知)"
    echo "     ファイル: $APP_DIR/.env"
fi

# ---- 7. ファイアウォール設定 ----
echo ""
echo "[7/9] UFW ファイアウォール設定..."
ufw --force reset > /dev/null
ufw default deny incoming
ufw default allow outgoing
ufw allow ssh
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable > /dev/null
echo "  ✅ UFW: $(ufw status | grep Status)"

# ---- 8. Fail2ban ----
echo ""
echo "[8/9] Fail2ban 設定..."
cat > /etc/fail2ban/jail.local <<'FAIL2BAN'
[DEFAULT]
bantime  = 3600
findtime = 600
maxretry = 5

[sshd]
enabled = true
port    = ssh

[nginx-http-auth]
enabled  = true
port     = http,https
logpath  = /var/log/nginx/buildee_error.log
FAIL2BAN
systemctl enable --now fail2ban > /dev/null 2>&1 || true
echo "  ✅ Fail2ban 設定完了"

# ---- 9. 初回デプロイ実行 ----
echo ""
echo "[9/9] 初回デプロイ実行..."
cd "$APP_DIR"
sudo -u "$APP_USER" bash deploy/scripts/deploy.sh
echo "  ✅ デプロイ完了"

# ---- 完了 ----
echo ""
echo "========================================================"
echo "  ✅ セットアップ完了!"
echo "========================================================"
echo ""
SERVER_IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo "  アクセス URL:  https://$SERVER_IP"
if [ -n "$APP_DOMAIN" ]; then
    echo "  ドメイン URL:  https://$APP_DOMAIN"
fi
echo ""
echo "  初回ログイン:"
echo "    ユーザー:   admin"
echo "    パスワード: admin1234  ← ⚠️ 必ず変更!"
echo ""
echo "  次のステップ:"
if [ -n "$APP_DOMAIN" ]; then
    echo "    Let's Encrypt 証明書取得:"
    echo "    bash deploy/scripts/certbot_init.sh $APP_DOMAIN admin@$APP_DOMAIN"
fi
echo "    GitHub Actions Secrets:"
echo "      PROD_HOST    = $SERVER_IP"
echo "      PROD_USER    = $APP_USER"
echo "      PROD_SSH_KEY = (C:\\Users\\tasayur\\.ssh\\buildee_deploy の内容)"
echo "      PROD_APP_DIR = $APP_DIR"
echo ""
docker ps --filter "name=buildee_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
