# BuildeeMgr 本番デプロイガイド

## 必要な環境

| 項目 | 要件 |
|------|------|
| OS | Ubuntu 22.04 / Debian 12 |
| CPU | 1コア以上 |
| メモリ | 1GB以上（推奨2GB） |
| ストレージ | 10GB以上 |
| ポート | 80, 443 |
| ドメイン | 任意（Let's Encrypt使用時は必須） |

---

## Step 1: サーバー初期設定

```bash
# サーバーにSSH接続後
git clone https://github.com/yourname/buildee_app.git /opt/buildee_app
cd /opt/buildee_app

# Docker・UFW・Fail2ban の一括セットアップ
sudo bash deploy/scripts/server_setup.sh
```

## Step 2: 環境設定

```bash
cp deploy/env.prod.example .env
nano .env   # 各値を本番用に変更
```

**必須変更項目:**
```env
SECRET_KEY=<python -c "import secrets; print(secrets.token_hex(32))" の出力>
MAIL_ENABLED=true
SMTP_USER=your@gmail.com
SMTP_PASSWORD=your_app_password
```

## Step 3: 自己署名証明書で起動（初回確認用）

```bash
bash deploy/scripts/deploy.sh
```

アクセス確認: `https://サーバーIP`

## Step 4: Let's Encrypt SSL証明書取得（ドメインがある場合）

```bash
# nginx/conf.d/buildee.conf の server_name を実ドメインに変更
sed -i 's/server_name  localhost/server_name  yourdomain.com/g' \
    nginx/conf.d/buildee.conf

# 証明書取得
bash deploy/scripts/certbot_init.sh yourdomain.com admin@yourdomain.com
```

## Step 5: 初回ログイン

```
URL:      https://yourdomain.com
ユーザー:  admin
パスワード: admin1234  ← 必ずすぐ変更
```

---

## 運用コマンド

```bash
# コンテナ状態確認
docker compose ps

# ログ確認（リアルタイム）
docker compose logs -f

# アプリのみ再起動
docker compose restart flask

# デプロイ（コード更新後）
bash deploy/scripts/deploy.sh

# ロールバック
bash deploy/scripts/rollback.sh

# バックアップ手動実行
docker exec buildee_flask python -c \
  "import backup_utils as bu; r=bu.run_scheduled_backup('manual'); print(r['filename'])"

# コンテナ内シェル
docker exec -it buildee_flask bash
```

---

## GitHub Actions 自動デプロイ設定

GitHub リポジトリの Settings → Secrets に以下を追加:

| Secret名 | 値 |
|---------|---|
| `PROD_HOST` | サーバーのIPアドレス |
| `PROD_USER` | SSHユーザー名（例: buildee） |
| `PROD_SSH_KEY` | SSH秘密鍵の内容 |
| `PROD_APP_DIR` | `/opt/buildee_app` |

main ブランチへの push で自動デプロイが実行されます。

---

## データ移行（既存環境から）

```bash
# 1. 既存環境でバックアップ作成
python -c "import backup_utils as bu; print(bu.create_backup('manual')['filename'])"

# 2. バックアップファイルを本番サーバーに転送
scp backups/buildee_manual_*.zip user@prod-server:/opt/buildee_app/backups/

# 3. 本番コンテナ内で復元
docker exec buildee_flask python -c "
import backup_utils as bu
r = bu.restore_backup('buildee_manual_XXXX.zip', ['buildee.db'])
print('Restored:', r['restored'])
"
```

---

## ディレクトリ構成（本番サーバー）

```
/opt/buildee_app/
├── .env               ← 本番設定（Git管理外）
├── docker-compose.yml
├── docker-compose.prod.yml
├── Dockerfile
├── nginx/
│   └── conf.d/buildee.conf  ← server_name を本番ドメインに変更
└── deploy/

Docker volumes (docker volume ls で確認):
  buildee_app_buildee_data     ← DB
  buildee_app_buildee_backups  ← バックアップ
  buildee_app_buildee_certs    ← 証明書
  buildee_app_certbot_conf     ← Let's Encrypt
```
