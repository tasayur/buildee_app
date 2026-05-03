#!/bin/bash
cd /c/Users/tasayur/Desktop/buildee_app

export FILTER_BRANCH_SQUELCH_WARNING=1
export GIT_AUTHOR_NAME="tasayur"
export GIT_COMMITTER_NAME="tasayur"

# Write correct message file in UTF-8
echo -n 'feat: BuildeeMgr v1.0.0 -- 施工管理システム完全版' > /tmp/correct_msg.txt

git filter-branch --force \
  --msg-filter '
    input=$(cat)
    if echo "$input" | grep -q "BuildeeMgr v1.0.0"; then
      cat /tmp/correct_msg.txt
    else
      echo "$input"
    fi
  ' \
  -- --all 2>&1

echo ""
echo "=== Result ==="
git --no-pager log --oneline -5
echo ""
git --no-pager log --format="%s" -2 HEAD~2..HEAD~1 2>/dev/null || true
git --no-pager log --format="%s" -1 HEAD~4 2>/dev/null || true
