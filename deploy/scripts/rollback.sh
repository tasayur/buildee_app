#!/bin/bash
# ================================================================
#  deploy/scripts/rollback.sh  -- BuildeeMgr ロールバック
#
#  使い方:
#    bash deploy/scripts/rollback.sh                    # 最新バックアップから復元
#    bash deploy/scripts/rollback.sh buildee_manual_xxx.zip
# ================================================================
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$APP_DIR"

TARGET_BACKUP="${1:-}"

echo "========================================"
echo "  BuildeeMgr ロールバック"
echo "========================================"

# ---- バックアップ一覧 ----
if [ -z "$TARGET_BACKUP" ]; then
    echo "利用可能なバックアップ:"
    docker exec buildee_flask python -c "
import backup_utils as bu
for i, b in enumerate(bu.list_backups()[:10], 1):
    print(f'  {i}. {b[\"filename\"]}  ({b[\"size\"]:,}B)  {b[\"timestamp\"]}')
" 2>/dev/null || ls -lt backups/*.zip 2>/dev/null | head -10 || echo "  バックアップが見つかりません"
    echo ""
    read -p "復元するバックアップファイル名を入力: " TARGET_BACKUP
fi

[ -z "$TARGET_BACKUP" ] && { echo "キャンセルしました。"; exit 0; }

echo ""
echo "復元対象: $TARGET_BACKUP"
read -p "本当に復元しますか？ (yes/no): " CONFIRM
[ "$CONFIRM" = "yes" ] || { echo "キャンセルしました。"; exit 0; }

# ---- 復元実行 ----
echo "データベースを復元中..."
docker exec buildee_flask python -c "
import backup_utils as bu
result = bu.restore_backup('$TARGET_BACKUP', ['buildee.db'])
if result['success']:
    print('✅ 復元完了:', result['restored'])
    print('   事前バックアップ:', result['pre_backup'])
else:
    print('❌ 復元失敗:', result['error'])
    exit(1)
"

# ---- Flask 再起動（DB キャッシュクリア） ----
echo "Flask を再起動中..."
docker compose restart flask
sleep 5

echo ""
echo "========================================"
echo "  ✅ ロールバック完了!"
echo "========================================"
