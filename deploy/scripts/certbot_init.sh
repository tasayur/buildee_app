#!/bin/bash
# ================================================================
#  deploy/scripts/certbot_init.sh
#  Let's Encrypt 証明書の初回取得スクリプト
#
#  使い方:
#    # 本番取得（--dry-run なし）
#    bash deploy/scripts/certbot_init.sh yourdomain.com admin@yourdomain.com
#
#    # ステージング（レート制限回避テスト）
#    bash deploy/scripts/certbot_init.sh yourdomain.com admin@yourdomain.com --staging
#
#    # 既存証明書があってもスキップせず強制取得
#    bash deploy/scripts/certbot_init.sh yourdomain.com admin@yourdomain.com --force
# ================================================================
set -euo pipefail

DOMAIN="${1:-}"
EMAIL="${2:-}"
STAGING=false
FORCE=false

for arg in "${@:3}"; do
    case "$arg" in
        --staging) STAGING=true ;;
        --force)   FORCE=true   ;;
    esac
done

# ---- 引数チェック ----
if [ -z "$DOMAIN" ] || [ -z "$EMAIL" ]; then
    echo "使い方: $0 <domain> <email> [--staging] [--force]"
    echo "例:     $0 buildee.example.com admin@example.com"
    exit 1
fi

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE="docker compose"
cd "$APP_DIR"

echo "========================================"
echo "  Let's Encrypt 証明書取得"
echo "  Domain:  $DOMAIN"
echo "  Email:   $EMAIL"
echo "  Staging: $STAGING"
echo "  Force:   $FORCE"
echo "========================================"

# ---- 前提確認 ----
command -v docker &>/dev/null || { echo "[ERROR] Docker が見つかりません"; exit 1; }
$COMPOSE ps nginx | grep -q "Up\|running" || {
    echo "[ERROR] Nginx コンテナが起動していません。先に 'docker compose up -d' を実行してください"
    exit 1
}

# ---- 既存証明書の確認 ----
CERT_PATH="/etc/letsencrypt/live/${DOMAIN}/fullchain.pem"
if docker compose run --rm certbot test -f "$CERT_PATH" 2>/dev/null && [ "$FORCE" = false ]; then
    echo "[INFO] 証明書は既に存在します。更新のみ行います。"
    echo "       強制再取得するには --force オプションを使用してください。"
    bash "$(dirname "$0")/certbot_renew.sh"
    exit 0
fi

# ---- Step 1: HTTP のみで動作確認（ACME チャレンジ用） ----
echo "[1/5] ACME チャレンジエンドポイントの確認..."
HTTP_CHECK=$(curl -s -o /dev/null -w "%{http_code}" \
    "http://${DOMAIN}/.well-known/acme-challenge/test" 2>/dev/null || echo "000")

if [ "$HTTP_CHECK" = "000" ]; then
    echo "[WARN] ドメイン $DOMAIN への HTTP アクセスができません。"
    echo "       DNS が正しく設定されているか確認してください。"
    echo "       （続行しますが、証明書取得に失敗する可能性があります）"
fi

# ---- Step 2: --dry-run で事前確認 ----
echo "[2/5] ドライランで事前確認..."
CERTBOT_CMD=(
    certbot certonly
    --webroot
    --webroot-path /var/www/certbot
    --email "$EMAIL"
    --agree-tos
    --no-eff-email
    -d "$DOMAIN"
    --dry-run
)
[ "$STAGING" = true ] && CERTBOT_CMD+=(--staging)

docker compose run --rm certbot "${CERTBOT_CMD[@]}" 2>&1 \
    && echo "   ✅ ドライラン成功" \
    || { echo "[ERROR] ドライラン失敗。DNS設定・ポート開放を確認してください。"; exit 1; }

# ---- Step 3: 本番取得 ----
echo "[3/5] 証明書を本番取得中..."
CERTBOT_CMD_PROD=(
    certbot certonly
    --webroot
    --webroot-path /var/www/certbot
    --email "$EMAIL"
    --agree-tos
    --no-eff-email
    -d "$DOMAIN"
)
[ "$STAGING" = true ] && CERTBOT_CMD_PROD+=(--staging)
[ "$FORCE"   = true ] && CERTBOT_CMD_PROD+=(--force-renewal)

docker compose run --rm certbot "${CERTBOT_CMD_PROD[@]}"
echo "   ✅ 証明書取得完了"

# ---- Step 4: Nginx 設定を Let's Encrypt 用に更新 ----
echo "[4/5] Nginx 設定を更新中..."
python3 -c "
import sys; sys.path.insert(0, '.')
import certbot_manager as cm
cm._update_nginx_for_letsencrypt('$DOMAIN')
print('   Nginx 設定更新完了')
" 2>/dev/null || {
    # Python が使えない場合は手動案内
    echo "   [INFO] Nginx 設定を手動で更新してください:"
    echo "   nginx/conf.d/buildee.conf の以下を変更:"
    echo "     ssl_certificate     /etc/letsencrypt/live/$DOMAIN/fullchain.pem;"
    echo "     ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;"
    echo "     server_name  $DOMAIN;"
}

# ---- Step 5: Nginx リロード + Certbot 自動更新サービス起動 ----
echo "[5/5] Nginx リロード & 自動更新サービス起動..."
$COMPOSE exec nginx nginx -s reload \
    && echo "   ✅ Nginx リロード完了" \
    || echo "   [WARN] Nginx リロード失敗（手動で 'docker compose exec nginx nginx -s reload' を実行）"

# Certbot 自動更新サービスを起動
$COMPOSE --profile ssl up -d certbot nginx-reload \
    && echo "   ✅ Certbot 自動更新サービス起動完了" \
    || echo "   [WARN] 自動更新サービスの起動に失敗しました"

echo ""
echo "========================================"
echo "  ✅ Let's Encrypt 証明書の設定完了!"
echo ""
echo "  アクセス先: https://$DOMAIN"
echo ""
echo "  証明書情報:"
docker compose run --rm --no-deps certbot \
    certbot certificates 2>/dev/null || true
echo ""
echo "  自動更新: 12時間ごとにチェック（期限30日前から更新実行）"
echo "  手動更新: bash deploy/scripts/certbot_renew.sh"
echo "  ログ確認: docker compose logs certbot"
echo "========================================"
