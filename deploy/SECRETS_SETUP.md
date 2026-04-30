# GitHub Actions Secrets 設定手順

## 設定が必要な Secrets 一覧

| Secret名 | 説明 | 例 |
|---------|------|---|
| `PROD_HOST` | サーバーのIPアドレス | `203.0.113.10` |
| `PROD_USER` | SSHログインユーザー名 | `buildee` |
| `PROD_SSH_KEY` | SSH秘密鍵（全文） | `-----BEGIN OPENSSH...` |
| `PROD_APP_DIR` | サーバー上のアプリパス | `/opt/buildee_app` |

---

## 手順

### 1. GitHub リポジトリの Settings を開く
```
https://github.com/tasayur/buildee_app/settings/secrets/actions
```

### 2. 各 Secret を登録

**New repository secret** をクリック → 名前と値を入力 → **Add secret**

---

### PROD_HOST
```
値: サーバーのIPアドレスまたはドメイン名
例: 203.0.113.10
```

### PROD_USER
```
値: buildee
```
（server_setup.sh で作成するユーザー名）

### PROD_SSH_KEY
秘密鍵の全文をそのままコピー（`-----BEGIN` から `-----END` まで）:

```
C:\Users\tasayur\.ssh\buildee_deploy の内容を貼り付け
```

PowerShell でコピー:
```powershell
Get-Content "$env:USERPROFILE\.ssh\buildee_deploy" | Set-Clipboard
```

### PROD_APP_DIR
```
値: /opt/buildee_app
```

---

## 確認方法

登録後、以下のページで4つが揃っていることを確認:
```
https://github.com/tasayur/buildee_app/settings/secrets/actions
```

---

## サーバー側への公開鍵登録（サーバー準備後に実施）

サーバー上で以下を実行:
```bash
# buildee ユーザーとして
mkdir -p ~/.ssh
chmod 700 ~/.ssh

# 以下の公開鍵を貼り付け:
echo "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILlpmCp+a0gyMePLjbRL8BJLO3aWgnqrj7qqZxiP8o/F buildee-deploy@github-actions" \
  >> ~/.ssh/authorized_keys

chmod 600 ~/.ssh/authorized_keys
```
