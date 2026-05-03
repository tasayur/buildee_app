#!/bin/bash
cd /c/Users/tasayur/Desktop/buildee_app

git config i18n.commitEncoding utf-8
git config i18n.logOutputEncoding utf-8
export FILTER_BRANCH_SQUELCH_WARNING=1

# perl は Git for Windows に含まれている
git filter-branch --force \
  --msg-filter 'perl -pe "s/.*\xef\xbd\xbd.*/feat: BuildeeMgr v1.0.0 -- \xe6\x96\xbd\xe5\xb7\xa5\xe7\xae\xa1\xe7\x90\x86\xe3\x82\xb7\xe3\x82\xb9\xe3\x83\x86\xe3\x83\xa0\xe5\xae\x8c\xe5\x85\xa8\xe7\x89\x88\n/g"' \
  -- --all 2>&1

echo "=== Result ==="
git log --oneline -5
