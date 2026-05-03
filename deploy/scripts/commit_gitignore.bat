@echo off
chcp 65001 > nul
set PATH=%PATH%;C:\Program Files\Git\cmd
cd /d C:\Users\tasayur\Desktop\buildee_app

echo Updating .gitignore for debug scripts...
(
echo.
echo # デバッグ用一時スクリプト
echo deploy/scripts/check_pat.ps1
echo deploy/scripts/check_repos.bat
echo deploy/scripts/check_ssh_keys.bat
echo deploy/scripts/check_user.ps1
echo deploy/scripts/create_repo.ps1
echo deploy/scripts/diag.ps1
echo deploy/scripts/gen_ssh.ps1
echo deploy/scripts/gen_ssh2.ps1
echo deploy/scripts/gen_github_key.bat
echo deploy/scripts/list_repos.bat
echo deploy/scripts/push_credential.bat
echo deploy/scripts/push_direct.ps1
echo deploy/scripts/setup_ssh_push.ps1
echo deploy/scripts/show_pubkey.ps1
echo deploy/scripts/ssh_test.bat
echo deploy/scripts/ssh_test2.bat
echo deploy/scripts/verify_key.bat
echo deploy/scripts/git_push.ps1
echo deploy/scripts/pat_curl_test.ps1
echo deploy/scripts/pat_len.ps1
echo deploy/scripts/git_commit_push.bat
) >> .gitignore

git add .gitignore
git commit -m "chore: ignore temporary debug scripts"
git log --oneline -4
echo Done.
