#!/bin/bash
# ================================================================
#  deploy/scripts/deploy.sh  -- BuildeeMgr デプロイスクリプト
#
#  使い方:
#    bash deploy/scripts/deploy.sh            # 通常デプロイ
#    bash deploy/scripts/deploy.sh --no-build # イメージ再利用
#    IMAGE_TAG=v1.2.3 bash deploy/scripts/deploy.sh
# ================================================================
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
COMPOSE="docker compose"
IMAGE_TAG="${IMAGE_TAG:-latest}"
NO_BUILD=false

for arg in "$@"; do
    case $arg in
        --no-build) NO_BUILD=true ;;
    esac
done

cd "$APP_DIR"

echo "========================================"
echo "  BuildeeMgr デプロイ開始"
echo "  DIR:       $APP_DIR"
echo "  IMAGE_TAG: $IMAGE_TAG"
echo "  NO_BUILD:  $NO_BUILD"
echo "========================================"

# ---- 前提確認 ----
[ -f ".env" ] || { echo "[ERROR] .env が見つかりません。deploy/env.prod.example をコピーして設定してください。"; exit 1; }
command -v docker &>/dev/null || { echo "[ERROR] Docker が見つかりません。"; exit 1; }

# ---- 1. バックアップ（デプロイ前） ----
echo "[1/6] デプロイ前バックアップ..."
if docker ps -q --filter "name=buildee_flask" | grep -q .; then
    docker exec buildee_flask python -c "
import backup_utils as bu
r = bu.run_scheduled_backup(bu.KIND_MANUAL)
print('Backup:', r.get('filename','failed'), '—', 'OK' if r.get('success') else r.get('error','?'))
" 2>/dev/null && echo "   バックアップ完了" || echo "   [WARN] バックアップ失敗（続行）"
else
    echo "   コンテナ未起動（スキップ）"
fi

# ---- 2. イメージビルド ----
if [ "$NO_BUILD" = false ]; then
    echo "[2/6] Docker イメージのビルド..."
    docker build -t "buildee_app:$IMAGE_TAG" -t "buildee_app:latest" . \
        --build-arg BUILDKIT_INLINE_CACHE=1
    echo "   ビルド完了"
else
    echo "[2/6] ビルドスキップ（--no-build）"
fi

# ---- 3. Nginx 設定確認 ----
echo "[3/6] Nginx 設定確認..."
docker run --rm -v "$APP_DIR/nginx:/etc/nginx:ro" nginx:1.27-alpine \
    nginx -t -c /etc/nginx/nginx.conf 2>&1 | tail -3 || true

# ---- 4. ローリング再起動 ----
echo "[4/6] アプリ再起動（ゼロダウンタイム）..."
IMAGE_TAG="$IMAGE_TAG" $COMPOSE \
    -f docker-compose.yml \
    -f docker-compose.prod.yml \
    up -d --no-deps flask
sleep 3

# ---- 5. ヘルスチェック ----
echo "[5/6] ヘルスチェック..."
MAX_WAIT=60
WAITED=0
until docker inspect --format='{{.State.Health.Status}}' buildee_flask 2>/dev/null | grep -q "healthy"; do
    if [ $WAITED -ge $MAX_WAIT ]; then
        echo "   [ERROR] ヘルスチェックタイムアウト（${MAX_WAIT}秒）"
        echo "   ログ確認: docker logs buildee_flask --tail=50"
        exit 1
    fi
    echo "   待機中... (${WAITED}s)"
    sleep 5
    WAITED=$((WAITED + 5))
done
echo "   ✅ Flask ヘルスチェック: healthy"

# ---- 6. Nginx 再起動 ----
echo "[6/6] Nginx リロード..."
IMAGE_TAG="$IMAGE_TAG" $COMPOSE \
    -f docker-compose.yml \
    -f docker-compose.prod.yml \
    up -d --no-deps nginx
echo "   ✅ Nginx 起動完了"

# ---- 完了 ----
echo ""
echo "========================================"
echo "  ✅ デプロイ完了!"
echo "========================================"
docker ps --filter "name=buildee_" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "  ログ確認:  docker compose logs -f"
echo "  状態確認:  docker compose ps"
