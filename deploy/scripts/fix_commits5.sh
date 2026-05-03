#!/bin/bash
cd /c/Users/tasayur/Desktop/buildee_app

export FILTER_BRANCH_SQUELCH_WARNING=1

# Write the correct message to a temp file (avoids encoding issues in shell)
TMPFILE=$(mktemp)
printf 'feat: BuildeeMgr v1.0.0 -- 施工管理システム完全版\n' > "$TMPFILE"

git filter-branch --force \
  --msg-filter "
    msg=\$(cat)
    if echo \"\$msg\" | grep -q 'BuildeeMgr v1.0.0'; then
      cat '$TMPFILE'
    else
      echo \"\$msg\"
    fi
  " \
  -- --all 2>&1

rm -f "$TMPFILE"

echo ""
echo "=== Result ==="
git log --oneline -5
git log --format="%s" -5
