@echo off
chcp 65001 > nul
set GIT="C:\Program Files\Git\cmd\git.exe"
cd /d C:\Users\tasayur\Desktop\buildee_app

echo === Step 1: Set UTF-8 encoding ===
%GIT% config --global i18n.commitEncoding utf-8
%GIT% config --global i18n.logOutputEncoding utf-8
%GIT% config --global core.quotepath false

echo === Step 2: Rewrite garbled commit messages ===
rem Use environment filter to fix message encoding
set FILTER_BRANCH_SQUELCH_WARNING=1

%GIT% filter-branch --force --msg-filter ^
"python -c ""import sys; msg=sys.stdin.buffer.read(); fixed=msg.replace(b'\xe8\xad\x81\xe3\x81\xbd\xe8\x9f\xbe\xe9\x82\x84\xe9\x80\x85\xe3\x83\xbb\xe3\x81\x99\xe7\xb9\xa7\xe3\x82\xb9\xe3\x83\x86\xe3\x83\xbb\xce\x92', b'\xe6\x96\xbd\xe5\xb7\xa5\xe7\xae\xa1\xe7\x90\x86\xe3\x82\xb7\xe3\x82\xb9\xe3\x83\x86\xe3\x83\xa0\xe5\xae\x8c\xe5\x85\xa8\xe7\x89\x88'); sys.stdout.buffer.write(fixed)""" ^
-- --all 2>&1

echo.
echo === Step 3: Check result ===
%GIT% log --oneline -5

echo.
echo Done. Push with force to GitHub.
pause
