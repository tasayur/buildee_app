#!/bin/bash
cd /c/Users/tasayur/Desktop/buildee_app

git config i18n.commitEncoding utf-8
git config i18n.logOutputEncoding utf-8
export FILTER_BRANCH_SQUELCH_WARNING=1

git filter-branch --force \
  --msg-filter 'python3 /c/Users/tasayur/Desktop/buildee_app/deploy/scripts/fix_msg_filter.py' \
  -- --all

echo "=== Result ==="
git log --oneline -5
