#!/bin/bash
cd /c/Users/tasayur/Desktop/buildee_app

git config i18n.commitEncoding utf-8
git config i18n.logOutputEncoding utf-8
export FILTER_BRANCH_SQUELCH_WARNING=1

CORRECT="feat: BuildeeMgr v1.0.0 -- 施工管理システム完全版"

git filter-branch --force \
  --msg-filter "perl -pe 's/feat: BuildeeMgr v1\.0\.0 -- .*/\Q${CORRECT}\E/g'" \
  -- --all 2>&1

echo ""
echo "=== Result ==="
git log --oneline -5
