# BuildeeMgr 本番展開後 全機能確認チェックリスト

> **確認日**: ____________  
> **サーバー**: ____________  
> **確認者**: ____________  
> 凡例: ✅ OK　❌ NG（詳細を備考欄に記録）

---

## 0. インフラ基盤

| # | 確認項目 | コマンド/手順 | 結果 | 備考 |
|---|---------|-------------|------|------|
| 0-1 | Docker コンテナ 3つが `Up` | `docker compose ps` | | flask / nginx / certbot |
| 0-2 | ポート 80/443 が LISTEN | `ss -tlnp \| grep -E '80\|443'` | | |
| 0-3 | HTTP → HTTPS リダイレクト | `curl -I http://ドメイン/` | | 301/302 が返ること |
| 0-4 | HTTPS アクセス可 | ブラウザで `https://ドメイン/` | | 証明書エラーなし |
| 0-5 | SSL 証明書の有効期限 | ブラウザ鍵マーク → 証明書 | | 90日以上残っていること |
| 0-6 | セキュリティヘッダー | `curl -I https://ドメイン/` | | CSP / HSTS / X-Frame-Options |
| 0-7 | ログ出力確認 | `docker compose logs flask \| tail -20` | | ERROR なし |
| 0-8 | DB ファイル確認 | `docker exec buildee_flask ls -lh /data/buildee.db` | | |
| 0-9 | ディスク空き容量 | `df -h /` | | 20% 以上空きがあること |

---

## 1. 認証・ユーザー管理

| # | 確認項目 | 手順 | 結果 | 備考 |
|---|---------|------|------|------|
| 1-1 | ログインページ表示 | `/login` にアクセス | | |
| 1-2 | admin ログイン | admin / admin1234 でログイン | | |
| 1-3 | **admin パスワード変更** ⚠️ | `/change-password` で即変更 | | **必須・最優先** |
| 1-4 | 誤パスワードで弾かれる | 間違ったパスで試行 | | エラーメッセージ表示 |
| 1-5 | ログアウト | `/logout` | | ログインページへ戻る |
| 1-6 | 未ログインでリダイレクト | ログアウト後 `/` にアクセス | | `/login` へ飛ぶこと |
| 1-7 | ユーザー新規作成 | 管理画面 → ユーザー管理 → 追加 | | manager/viewer ロール |
| 1-8 | ユーザー編集・削除 | 作成したユーザーを編集・削除 | | |
| 1-9 | パスワードリセット | 管理画面から対象ユーザーをリセット | | |
| 1-10 | RBAC: viewer は管理画面に入れない | viewer でログイン → `/admin/users` | | 403 または非表示 |
| 1-11 | ログイン履歴 | DB 確認 or ログ確認 | | `login_log` テーブル |

---

## 2. ダッシュボード・TOP

| # | 確認項目 | 手順 | 結果 | 備考 |
|---|---------|------|------|------|
| 2-1 | ダッシュボード表示 | `/` にアクセス | | |
| 2-2 | API `/api/dashboard` | レスポンス 200 | | |
| 2-3 | ナビゲーション全リンク | 各メニューをクリック | | 404 なし |
| 2-4 | レスポンシブ表示 | スマホ幅でアクセス | | ハンバーガーメニュー |
| 2-5 | オフラインページ | `/offline` にアクセス | | |

---

## 3. 調整会議（工程・機材）

| # | 確認項目 | 手順 | 結果 | 備考 |
|---|---------|------|------|------|
| 3-1 | 調整会議ページ表示 | `/coordination` | | |
| 3-2 | 会社登録 | `POST /api/companies` | | |
| 3-3 | 会社一覧取得 | `GET /api/companies` | | |
| 3-4 | 工程追加 | 画面から工程を追加 | | |
| 3-5 | 工程一覧 | `GET /api/schedules` | | |
| 3-6 | 工程編集 | `PUT /api/schedules/<sid>` | | |
| 3-7 | 工程削除 | `DELETE /api/schedules/<sid>` | | |
| 3-8 | 機材追加 | `POST /api/equipment` | | |
| 3-9 | 機材一覧 | `GET /api/equipment` | | |
| 3-10 | 機材削除 | `DELETE /api/equipment/<eid>` | | |

---

## 4. KY（危険予知）活動

| # | 確認項目 | 手順 | 結果 | 備考 |
|---|---------|------|------|------|
| 4-1 | KYページ表示 | `/ky` | | |
| 4-2 | KY記録追加 | `POST /api/ky` | | |
| 4-3 | KY一覧取得 | `GET /api/ky` | | |
| 4-4 | KY承認 | `PUT /api/ky/<kid>/approve` | | manager以上のみ |
| 4-5 | viewer は承認できない | viewer でログインして承認試行 | | 403 が返ること |

---

## 5. 労務安全書類

| # | 確認項目 | 手順 | 結果 | 備考 |
|---|---------|------|------|------|
| 5-1 | 安全書類ページ表示 | `/safety` | | |
| 5-2 | 作業員追加 | `POST /api/workers` | | |
| 5-3 | 作業員一覧 | `GET /api/workers` | | |
| 5-4 | 作業員削除 | `DELETE /api/workers/<wid>` | | |
| 5-5 | 安全書類登録 | `POST /api/safety_docs` | | |
| 5-6 | 安全書類一覧 | `GET /api/safety_docs` | | |

---

## 6. 入退場管理・QRコード

| # | 確認項目 | 手順 | 結果 | 備考 |
|---|---------|------|------|------|
| 6-1 | 入退場ページ表示 | `/attendance` | | |
| 6-2 | QRゲートページ表示 | `/qr-gate` | | |
| 6-3 | 作業員 QR 取得 | `GET /api/qr/worker/<wid>` | | PNG が返ること |
| 6-4 | QR 再生成 | `POST /api/qr/worker/<wid>/regenerate` | | |
| 6-5 | QR 一括生成 | `POST /api/qr/bulk-generate` | | |
| 6-6 | QR スキャン（入場） | `POST /api/qr/scan` body: `{"qr_code":"...","action":"in"}` | | |
| 6-7 | QR スキャン（退場） | `POST /api/qr/scan` body: `{"qr_code":"...","action":"out"}` | | |
| 6-8 | 入場記録一覧 | `GET /api/attendance` | | |
| 6-9 | 直接入場 | `POST /api/attendance/checkin` | | |
| 6-10 | 直接退場 | `POST /api/attendance/checkout` | | |
| 6-11 | スマホカメラでQR読み取り | QRゲート画面でカメラ起動 | | HTTPS 必須 |

---

## 7. Excel エクスポート

| # | 確認項目 | 手順 | 結果 | 備考 |
|---|---------|------|------|------|
| 7-1 | エクスポートページ表示 | `/export` | | |
| 7-2 | Excel 生成（フル） | `POST /api/export` | | .xlsx ダウンロード |
| 7-3 | クイックエクスポート | `GET /api/export/quick/<sn>` | | シート名指定 |
| 7-4 | 7シート全て含まれる | ダウンロードした xlsx を開く | | 調整/KY/安全/入退場/etc |
| 7-5 | データが正しく入っている | 各シートのデータ確認 | | |

---

## 8. PWA（プログレッシブウェブアプリ）

| # | 確認項目 | 手順 | 結果 | 備考 |
|---|---------|------|------|------|
| 8-1 | manifest.json 取得 | `/static/manifest.json` | | 200 |
| 8-2 | Service Worker 登録 | DevTools → Application → Service Workers | | Activated |
| 8-3 | インストールプロンプト | Chrome でアクセス → アドレスバーにインストールアイコン | | |
| 8-4 | オフライン動作 | DevTools → Network → Offline → リロード | | オフラインページ表示 |
| 8-5 | アイコン表示 | インストール後のアイコン確認 | | |

---

## 9. メール通知

| # | 確認項目 | 手順 | 結果 | 備考 |
|---|---------|------|------|------|
| 9-1 | メール設定確認 | `GET /api/notifications/settings` | | |
| 9-2 | SMTP 接続状態 | `GET /api/notifications/mail-status` | | |
| 9-3 | テストメール送信 | `POST /api/notifications/test` | | 受信ボックス確認 |
| 9-4 | 通知ログ確認 | `GET /api/notifications/log` | | |
| 9-5 | 証明書チェック実行 | `POST /api/notifications/run-cert-check` | | |
| 9-6 | 管理画面から設定変更 | `/admin/notifications` | | |

---

## 10. バックアップ

| # | 確認項目 | 手順 | 結果 | 備考 |
|---|---------|------|------|------|
| 10-1 | バックアップ管理画面 | `/admin/backup` | | |
| 10-2 | 手動バックアップ実行 | `POST /api/backup/run` | | |
| 10-3 | バックアップ一覧 | `GET /api/backup/list` | | .zip が表示される |
| 10-4 | バックアップログ | `GET /api/backup/log` | | |
| 10-5 | バックアップ検証 | `GET /api/backup/verify/<filename>` | | |
| 10-6 | バックアップダウンロード | `GET /api/backup/download/<filename>` | | |
| 10-7 | バックアップ設定確認 | `GET /api/backup/settings` | | 日次/週次/月次スケジュール |
| 10-8 | 自動バックアップ設定 | `POST /api/backup/settings` | | |
| 10-9 | バックアップ削除 | `DELETE /api/backup/delete/<filename>` | | |
| 10-10 | バックアップから復元 | `POST /api/backup/restore` （テスト環境で） | | **本番DBは慎重に** |

---

## 11. SSL/TLS 証明書管理

| # | 確認項目 | 手順 | 結果 | 備考 |
|---|---------|------|------|------|
| 11-1 | 証明書管理画面 | `/admin/cert` | | |
| 11-2 | 証明書情報 API | `GET /api/admin/cert-info` | | 有効期限表示 |
| 11-3 | Let's Encrypt 状態 | `GET /api/admin/certbot/status` | | |
| 11-4 | 証明書更新ログ | `GET /api/admin/certbot/log` | | |
| 11-5 | 自動更新スケジュール | cron / docker certbot 確認 | | `docker compose logs certbot` |

---

## 12. セキュリティ確認

| # | 確認項目 | コマンド/手順 | 結果 | 備考 |
|---|---------|-------------|------|------|
| 12-1 | CSP ヘッダー | `curl -I https://ドメイン/ \| grep -i content-security` | | |
| 12-2 | HSTS ヘッダー | `curl -I https://ドメイン/ \| grep -i strict-transport` | | |
| 12-3 | X-Frame-Options | `curl -I https://ドメイン/ \| grep -i x-frame` | | DENY/SAMEORIGIN |
| 12-4 | X-Content-Type-Options | `curl -I https://ドメイン/ \| grep -i x-content` | | nosniff |
| 12-5 | .env が公開されていない | `curl https://ドメイン/.env` | | 404 が返ること |
| 12-6 | /admin は認証必須 | 未ログインで `/admin/users` | | リダイレクトされる |
| 12-7 | Fail2ban 稼働 | `sudo fail2ban-client status` | | |
| 12-8 | UFW 設定 | `sudo ufw status` | | 80/443/SSH のみ |

---

## 13. 負荷・パフォーマンス（任意）

| # | 確認項目 | 手順 | 結果 | 備考 |
|---|---------|------|------|------|
| 13-1 | ページ応答速度 | DevTools → Network → 各ページ | | 3秒以内が目標 |
| 13-2 | 同時アクセス | `ab -n 100 -c 10 https://ドメイン/` | | エラーなし |
| 13-3 | メモリ使用量 | `docker stats --no-stream` | | |
| 13-4 | Gunicorn ワーカー | `docker exec buildee_flask ps aux` | | |

---

## 確認完了後の作業

```bash
# 1. admin パスワード変更（必須）
# ブラウザ: https://ドメイン/change-password

# 2. GitHub Actions Secrets 設定
# PROD_HOST / PROD_USER / PROD_SSH_KEY / PROD_APP_DIR

# 3. 定期バックアップ設定
# /admin/backup → スケジュール設定

# 4. メール通知設定
# /admin/notifications → SMTP設定 → テスト送信

# 5. ドメイン取得後 Let's Encrypt 証明書取得
# bash deploy/scripts/certbot_init.sh yourdomain.com admin@yourdomain.com
```

---

## 緊急時の対応

```bash
# アプリが落ちた
docker compose restart flask

# 全コンテナ再起動
docker compose down && docker compose up -d

# ロールバック
bash deploy/scripts/rollback.sh

# ログで原因確認
docker compose logs flask --tail=100
```

---

*最終更新: 本番展開時に更新してください*
