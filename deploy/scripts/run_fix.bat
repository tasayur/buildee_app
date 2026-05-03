@echo off
chcp 65001 > nul
set GIT="C:\Program Files\Git\cmd\git.exe"
set PYTHON="C:\Program Files\Git\usr\bin\python3.exe"
cd /d C:\Users\tasayur\Desktop\buildee_app

echo === Fixing commit message encoding ===
set FILTER_BRANCH_SQUELCH_WARNING=1

%GIT% config i18n.commitEncoding utf-8
%GIT% config i18n.logOutputEncoding utf-8

%GIT% filter-branch --force --msg-filter "%PYTHON% deploy\scripts\fix_msg.py" -- --all 2>&1

echo.
echo === Result ===
%GIT% log --oneline -5
pause
