#!/bin/bash
# 文字化けした2コミット (aa6e6b0, e3b321f) を特定ハッシュで判定して修正
cd /c/Users/tasayur/Desktop/buildee_app

export FILTER_BRANCH_SQUELCH_WARNING=1

HASH1="aa6e6b0ecb6185a21ca0ef153e41684dafd76f88"
HASH2="e3b321f50a0340b9c6750970fb9d7071aa69adb2"
CORRECT="feat: BuildeeMgr v1.0.0 -- 施工管理システム完全版"

git filter-branch --force \
  --msg-filter '
    COMMIT_HASH=$(git log --format="%H" HEAD..HEAD 2>/dev/null || echo "")
    cat
  ' \
  --commit-filter '
    if [ "$GIT_COMMIT" = "'"$HASH1"'" ] || [ "$GIT_COMMIT" = "'"$HASH2"'" ]; then
      export GIT_AUTHOR_NAME="$GIT_AUTHOR_NAME"
      git commit-tree "$@" <<< "'"$CORRECT"'"
    else
      git commit-tree "$@"
    fi
  ' \
  -- --all 2>&1

echo "=== Result ==="
git --no-pager log --oneline -5
