@echo off
chcp 65001 > nul
set PATH=%PATH%;C:\Program Files\Git\cmd;C:\Program Files\Git\bin
set GIT="C:\Program Files\Git\cmd\git.exe"
cd /d C:\Users\tasayur\Desktop\buildee_app

echo === Git encoding fix ===
%GIT% config --global i18n.commitEncoding utf-8
%GIT% config --global i18n.logOutputEncoding utf-8
%GIT% config --global core.quotepath false

echo.
echo === Current log ===
%GIT% log --oneline -5

echo.
echo === Fixing commit messages (interactive rebase) ===
echo The 2 garbled commits will be reworded to:
echo   "feat: BuildeeMgr v1.0.0 -- 施工管理システム完全版"

rem Use rebase to fix the 2 oldest commits
rem bdc9f8c = root commit, 317aa99 = second commit
rem We'll use filter-branch to rewrite both

%GIT% filter-branch -f --msg-filter "
python3 -c \"
import sys, codecs
msg = sys.stdin.buffer.read()
try:
    decoded = msg.decode('utf-8')
except:
    try:
        decoded = msg.decode('cp932')
    except:
        decoded = msg.decode('latin-1')
fixed = decoded.replace('譁ｽ蟾･邂｡逅・す繧ｹ繝・Β', '施工管理システム完全版')
sys.stdout.buffer.write(fixed.encode('utf-8'))
\"
" -- bdc9f8c^..317aa99 2>&1

echo.
echo === Log after fix ===
%GIT% log --oneline -5
echo.
pause
