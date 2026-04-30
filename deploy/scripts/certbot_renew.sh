#!/bin/bash
# ================================================================
#  deploy/scripts/certbot_renew.sh
#  Let's Encrypt 証明書の手動更新
#
#  使い方:
#    bash deploy/scripts/certbot_renew.sh           # 通常更新
#    bash deploy/scripts/certbot_renew.sh --dry-run # ドライラン
#    bash deploy/scripts/certbot_renew.sh --force   # 強制更新
# ================================================================
set -euo pipefail

DRY_RUN=false
FORCE=false

for arg in "$@"; do
    case "$arg" in
        --dry-run) DRY_RUN=true ;;
        --force)   FORCE=true   ;;
    esac
done

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE="docker compose"
cd "$APP_DIR"

echo "========================================"
echo "  Let's Encrypt 証明書更新"
echo "  Dry-run: $DRY_RUN"
echo "  Force:   $FORCE"
echo "========================================"

# ---- 証明書の現状確認 ----
echo "[1/3] 証明書の有効期限確認..."
docker compose run --rm --no-deps certbot \
    certbot certificates 2>/dev/null || echo "   (certbot コンテナが停止中)"

# ---- 更新実行 ----
echo "[2/3] 更新実行..."
RENEW_CMD=(certbot renew)
[ "$DRY_RUN" = true ] && RENEW_CMD+=(--dry-run)
[ "$FORCE"   = true ] && RENEW_CMD+=(--force-renewal)

# certbot コンテナが起動中か確認
if $COMPOSE ps certbot 2>/dev/null | grep -q "running\|Up"; then
    docker compose exec certbot "${RENEW_CMD[@]}"
else
    docker compose run --rm certbot "${RENEW_CMD[@]}"
fi

echo "   ✅ 更新処理完了"

# ---- Nginx リロード ----
if [ "$DRY_RUN" = false ]; then
    echo "[3/3] Nginx をリロード..."
    $COMPOSE exec nginx nginx -s reload \
        && echo "   ✅ Nginx リロード完了" \
        || echo "   [WARN] Nginx リロードに失敗しました"
else
    echo "[3/3] ドライランのため Nginx リロードをスキップ"
fi

echo ""
echo "========================================"
echo "  完了!"
if [ "$DRY_RUN" = true ]; then
    echo "  ※ --dry-run のため実際の更新は行われていません"
fi
echo "========================================"
