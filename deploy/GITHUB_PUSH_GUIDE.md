# BuildeeMgr GitHub プッシュ & 本番展開ガイド

> Git の初回コミット（69ファイル）は完了済みです。
> このガイドの手順を上から順に実行してください。

---

## Part 1: GitHub リポジトリ作成 & プッシュ

### Step 1: Personal Access Token (PAT) の作成

1. [https://github.com/settings/tokens](https://github.com/settings/tokens) を開く
2. **"Generate new token (classic)"** をクリック
3. 設定:
   - Note: `buildee_deploy`
   - Expiration: `90 days`（または No expiration）
   - Scopes: ✅ **repo**（Full control of private repositories）
4. **"Generate token"** をクリック → トークンをコピー（一度しか表示されない）

---

### Step 2: GitHub リポジトリの作成

1. [https://github.com/new](https://github.com/new) を開く
2. 設定:
   - Repository name: `buildee_app`
   - Visibility: **Private**（推奨）
   - README, .gitignore, license: **追加しない**（既にローカルにある）
3. **"Create repository"** をクリック

---

### Step 3: PowerShell でプッシュ

PowerShell を開き（管理者不要）、以下を実行：

```powershell
# Git のパスを通す
$env:PATH += ";C:\Program Files\Git\cmd"

# プロジェクトフォルダに移動
cd "C:\Users\tasayur\Desktop\buildee_app"

# リモートを設定（YOUR_USERNAME と YOUR_TOKEN を置き換える）
git remote add origin https://YOUR_USERNAME:YOUR_TOKEN@github.com/YOUR_USERNAME/buildee_app.git

# プッシュ
git push -u origin main
```

**実行例:**
```powershell
$env:PATH += ";C:\Program Files\Git\cmd"
cd "C:\Users\tasayur\Desktop\buildee_app"
git remote add origin https://yamada-taro:ghp_xxxxxxxxxxxx@github.com/yamada-taro/buildee_app.git
git push -u origin main
```

---

### Step 4: プッシュ確認

```
https://github.com/YOUR_USERNAME/buildee_app
```
69ファイルが表示されれば成功です。

---

## Part 2: 本番サーバーのセットアップ

### Step 5: サーバーに SSH 接続

```bash
ssh ubuntu@YOUR_SERVER_IP
```

### Step 6: サーバー初期設定（Docker・UFW・Fail2ban）

```bash
# リポジトリをクローン
git clone https://github.com/YOUR_USERNAME/buildee_app.git /opt/buildee_app
cd /opt/buildee_app

# サーバーセットアップ（Docker・UFW・Fail2ban を一括インストール）
sudo bash deploy/scripts/server_setup.sh
```

### Step 7: 環境設定

```bash
cd /opt/buildee_app

# 本番用 .env を作成
cp deploy/env.prod.example .env
nano .env
```

`.env` で**必ず変更する項目**:
```env
# セキュリティキー（以下のコマンドで生成）
# python3 -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=ここに32文字以上のランダム文字列

# メール通知
MAIL_ENABLED=true
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_16char_app_password
SMTP_FROM=BuildeeMgr <your@gmail.com>
```

### Step 8: 初回デプロイ

```bash
bash deploy/scripts/deploy.sh
```

自動で以下が実行されます:
1. Docker イメージのビルド
2. Flask コンテナのヘルスチェック
3. Nginx の起動

### Step 9: アクセス確認

```
https://YOUR_SERVER_IP
初期ログイン: admin / admin1234
```

⚠️ **初回ログイン後すぐにパスワードを変更してください**

---

## Part 3: GitHub Actions 自動デプロイの設定

### Step 10: SSH 鍵の設定（サーバー側）

```bash
# サーバーで SSH 鍵ペアを生成
ssh-keygen -t ed25519 -C "github-deploy" -f ~/.ssh/github_deploy -N ""

# 公開鍵を authorized_keys に追加
cat ~/.ssh/github_deploy.pub >> ~/.ssh/authorized_keys

# 秘密鍵の内容をコピー（GitHub に登録する）
cat ~/.ssh/github_deploy
```

### Step 11: GitHub Secrets の設定

[https://github.com/YOUR_USERNAME/buildee_app/settings/secrets/actions](https://github.com/YOUR_USERNAME/buildee_app/settings/secrets/actions)

**"New repository secret"** で以下を追加:

| Secret 名 | 値 |
|-----------|---|
| `PROD_HOST` | サーバーのIP（例: `203.0.113.1`） |
| `PROD_USER` | SSHユーザー名（例: `ubuntu`） |
| `PROD_SSH_KEY` | `~/.ssh/github_deploy` の内容（`-----BEGIN` から最後まで） |
| `PROD_APP_DIR` | `/opt/buildee_app` |

### Step 12: 動作確認

```bash
# ローカルで変更してプッシュ → 自動デプロイが走る
cd "C:\Users\tasayur\Desktop\buildee_app"
$env:PATH += ";C:\Program Files\Git\cmd"

# 何か変更して
git add -A
git commit -m "test: CI/CD 動作確認"
git push
```

GitHub の **Actions タブ**でパイプラインを確認:
`https://github.com/YOUR_USERNAME/buildee_app/actions`

---

## Part 4: Let's Encrypt SSL（ドメインがある場合）

### Step 13: 証明書取得

```bash
cd /opt/buildee_app

# ドメインが DNS でサーバーを向いていることを確認してから実行
bash deploy/scripts/certbot_init.sh yourdomain.com admin@yourdomain.com
```

### Step 14: 自動更新の有効化

```bash
docker compose --profile ssl up -d
docker compose logs certbot  # ログ確認
```

---

## 運用コマンド早見表

```bash
# アプリ状態確認
docker compose ps

# ログ確認
docker compose logs -f

# 手動バックアップ
docker exec buildee_flask python -c "import backup_utils as bu; r=bu.run_scheduled_backup('manual'); print(r['filename'])"

# 証明書確認
bash deploy/scripts/cert_check.sh

# ロールバック
bash deploy/scripts/rollback.sh

# コード更新デプロイ
git pull origin main
bash deploy/scripts/deploy.sh
```

---

## トラブルシューティング

| 問題 | 確認コマンド |
|------|------------|
| アプリが起動しない | `docker compose logs flask` |
| Nginx エラー | `docker compose logs nginx` |
| ヘルスチェック失敗 | `docker exec buildee_flask python -c "import app"` |
| 証明書エラー | `bash deploy/scripts/cert_check.sh` |
| DB破損 | `bash deploy/scripts/rollback.sh` |
