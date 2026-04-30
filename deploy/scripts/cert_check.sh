#!/bin/bash
# ================================================================
#  deploy/scripts/cert_check.sh
#  証明書の有効期限確認（cron で定期実行可能）
#
#  cron 設定例（毎朝8時に確認）:
#    0 8 * * * /opt/buildee_app/deploy/scripts/cert_check.sh >> /var/log/cert_check.log 2>&1
# ================================================================
set -euo pipefail

APP_DIR="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$APP_DIR"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 証明書確認開始"

# ---- Docker 経由で確認 ----
if command -v docker &>/dev/null; then
    echo "--- Let's Encrypt 証明書 ---"
    docker run --rm \
        -v "$(docker volume ls -q --filter name=certbot_conf 2>/dev/null | head -1 || echo buildee_app_certbot_conf):/etc/letsencrypt:ro" \
        certbot/certbot certificates 2>/dev/null \
        | grep -E "Domains:|Expiry Date:|VALID|EXPIRED|WARNING" || echo "  (証明書なし)"

    echo ""
    echo "--- 自己署名証明書 ---"
    docker exec buildee_flask python -c "
import certbot_manager as cm
info = cm.get_all_cert_status()
ss   = info['self_signed']
le   = info['letsencrypt']

if ss.get('exists'):
    days = ss.get('days_left','?')
    print(f'  自己署名: {ss.get(\"cn\",\"?\")}, 期限: {ss.get(\"not_after\",\"?\")}, 残り: {days}日')

if le.get('exists'):
    days = le.get('days_left','?')
    status = '⚠️  更新必要' if le.get('expiring') else ('🚨 期限切れ' if le.get('expired') else '✅ 有効')
    print(f'  LE証明書: {le.get(\"domain\",\"?\")}, 期限: {le.get(\"not_after\",\"?\")}, 残り: {days}日 {status}')
else:
    print('  LE証明書: なし（自己署名を使用中）')
" 2>/dev/null || echo "  (Flask コンテナ未起動)"

else
    # Docker なし — openssl で直接確認
    CERT_FILES=(
        "certs/buildee.crt"
        "/etc/letsencrypt/live/*/fullchain.pem"
    )
    for pattern in "${CERT_FILES[@]}"; do
        for cert in $pattern; do
            [ -f "$cert" ] || continue
            expiry=$(openssl x509 -enddate -noout -in "$cert" 2>/dev/null | cut -d= -f2)
            cn=$(openssl x509 -subject -noout -in "$cert" 2>/dev/null | grep -o 'CN=.*' | cut -d= -f2 | cut -d, -f1)
            echo "  $cert: CN=$cn, 期限=$expiry"
        done
    done
fi

echo "[$(date '+%Y-%m-%d %H:%M:%S')] 確認完了"
