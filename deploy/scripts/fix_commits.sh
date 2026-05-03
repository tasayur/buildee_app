#!/bin/bash
# コミットメッセージの文字化けを修正する
cd /c/Users/tasayur/Desktop/buildee_app

echo "=== Before fix ==="
git log --oneline -5

echo ""
echo "=== Fixing encoding ==="
git config i18n.commitEncoding utf-8
git config i18n.logOutputEncoding utf-8

export FILTER_BRANCH_SQUELCH_WARNING=1

git filter-branch --force --msg-filter '
python3 -c "
import sys
msg = sys.stdin.buffer.read().decode(\"utf-8\", errors=\"replace\")
garbled_patterns = [\"譁ｽ蟾･邂｡逅\", \"す繧ｹ繝\", \"繧ｹ繝・Β\"]
needs_fix = any(p in msg for p in garbled_patterns)
if needs_fix:
    msg = \"feat: BuildeeMgr v1.0.0 -- 施工管理システム完全版\n\"
sys.stdout.buffer.write(msg.encode(\"utf-8\"))
"
' -- --all

echo ""
echo "=== After fix ==="
git log --oneline -5
