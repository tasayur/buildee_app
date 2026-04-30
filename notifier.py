# notifier.py -- BuildeeMgr 通知エンジン
# 全通知トリガーの定義・DB記録・テンプレート生成
import sqlite3, uuid, logging, threading
from datetime import datetime, date, timedelta
from typing   import List, Optional
import database as db
import mail_utils as mu

log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Notification log DB
# ------------------------------------------------------------------
def _conn():
    import database
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_notification_db():
    """Create notification tables."""
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS notification_log (
                id          TEXT PRIMARY KEY,
                event_type  TEXT NOT NULL,
                subject     TEXT NOT NULL,
                recipients  TEXT NOT NULL,
                status      TEXT NOT NULL,
                error_msg   TEXT,
                related_id  TEXT,
                created_at  TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_notif_type
                ON notification_log(event_type);
            CREATE INDEX IF NOT EXISTS idx_notif_ts
                ON notification_log(created_at);

            CREATE TABLE IF NOT EXISTS notification_settings (
                key   TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        # Default settings
        defaults = {
            'ky_approve_enabled':       'true',
            'attendance_enabled':       'false',
            'cert_expiry_enabled':      'true',
            'cert_expiry_days':         '30',
            'daily_report_enabled':     'false',
            'daily_report_hour':        '8',
            'admin_emails':             '',
            'site_url':                 'https://localhost:5443',
            # バックアップ設定
            'backup_enabled':           'true',
            'backup_hour':              '2',      # 毎日午前2時
            'backup_notify_success':    'false',  # 成功時もメール通知するか
            'backup_keep_daily':        '7',
            'backup_keep_weekly':       '4',
            'backup_keep_monthly':      '3',
        }
        for k, v in defaults.items():
            conn.execute(
                "INSERT OR IGNORE INTO notification_settings(key,value) VALUES(?,?)",
                (k, v)
            )

def get_setting(key: str, default: str = '') -> str:
    with _conn() as conn:
        row = conn.execute(
            "SELECT value FROM notification_settings WHERE key=?", (key,)
        ).fetchone()
        return row['value'] if row else default

def set_setting(key: str, value: str):
    with _conn() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO notification_settings(key,value) VALUES(?,?)",
            (key, value)
        )

def get_all_settings() -> dict:
    with _conn() as conn:
        rows = conn.execute("SELECT key, value FROM notification_settings").fetchall()
        return {r['key']: r['value'] for r in rows}

def get_admin_emails() -> List[str]:
    raw = get_setting('admin_emails', '')
    return [e.strip() for e in raw.split(',') if e.strip() and '@' in e]

def _log_notification(event_type, subject, recipients, success, error_msg='', related_id=''):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO notification_log
            (id, event_type, subject, recipients, status, error_msg, related_id)
            VALUES (?,?,?,?,?,?,?)
        """, (
            str(uuid.uuid4()), event_type, subject,
            ', '.join(recipients) if isinstance(recipients, list) else recipients,
            'sent' if success else 'failed',
            error_msg or '', related_id or ''
        ))

def get_notification_log(limit: int = 50) -> list:
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM notification_log ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        return [dict(r) for r in rows]

def get_notification_stats() -> dict:
    with _conn() as conn:
        total = conn.execute("SELECT COUNT(*) FROM notification_log").fetchone()[0]
        sent  = conn.execute(
            "SELECT COUNT(*) FROM notification_log WHERE status='sent'"
        ).fetchone()[0]
        today_count = conn.execute(
            "SELECT COUNT(*) FROM notification_log WHERE date(created_at)=date('now','localtime')"
        ).fetchone()[0]
        return {'total': total, 'sent': sent, 'failed': total - sent, 'today': today_count}


# ------------------------------------------------------------------
# Fire-and-forget async sender
# ------------------------------------------------------------------
def _send_async(msg: mu.MailMessage, event_type: str, related_id: str = ''):
    """Send mail in background thread — never blocks the request."""
    def _run():
        ok, err = mu.send_mail(msg)
        _log_notification(event_type, msg.subject, msg.to, ok, err, related_id)
        if not ok and err != 'disabled':
            log.error(f"[Notifier] {event_type} failed: {err}")
    threading.Thread(target=_run, daemon=True).start()


# ==================================================================
#  Trigger 1: KY 承認通知
# ==================================================================
def notify_ky_approved(ky_id: str, ky_data: dict, approved_by: str):
    """KY記録が承認された時に管理者・関係者へ通知。"""
    if get_setting('ky_approve_enabled') != 'true':
        return
    recipients = get_admin_emails()
    if not recipients:
        log.info("[Notifier] ky_approved: no admin_emails configured")
        return

    company     = ky_data.get('company', '—')
    danger      = ky_data.get('danger_point', '—')
    measure     = ky_data.get('measure', '—')
    level       = ky_data.get('level', '—')
    record_date = ky_data.get('date', date.today().isoformat())
    site_url    = get_setting('site_url')

    subject = f'【BuildeeMgr】KY記録が承認されました — {company}'
    body_text = (
        f'KY記録が承認されました。\n\n'
        f'承認者   : {approved_by}\n'
        f'会社     : {company}\n'
        f'日付     : {record_date}\n'
        f'危険ポイント: {danger}\n'
        f'対策     : {measure}\n'
        f'リスクレベル: {level}\n\n'
        f'確認: {site_url}/ky\n'
        '---\nBuildee 施工管理システム'
    )
    body_html = mu._html_wrap(
        'KY記録 承認通知',
        f'''<p><strong>{company}</strong> のKY記録が承認されました。</p>
        <table>
          <tr><th>承認者</th><td>{approved_by}</td></tr>
          <tr><th>日付</th><td>{record_date}</td></tr>
          <tr><th>危険ポイント</th><td>{danger}</td></tr>
          <tr><th>対策</th><td>{measure}</td></tr>
          <tr><th>リスクレベル</th>
              <td><span class="badge" style="background:{'#fef2f2;color:#dc2626' if level=='高' else '#fff7ed;color:#c2410c' if level=='中' else '#dcfce7;color:#166534'}">{level}</span></td></tr>
        </table>
        <p><a href="{site_url}/ky" style="color:#f97316">→ KYページで確認する</a></p>''',
        color='#10b981'
    )
    msg = mu.MailMessage(recipients, subject, body_text, body_html)
    _send_async(msg, 'ky_approved', ky_id)


# ==================================================================
#  Trigger 2: 入退場通知
# ==================================================================
def notify_attendance(worker: dict, action: str, att_date: str, time_str: str):
    """入場・退場時に管理者へ通知（設定で個別ON/OFF）。"""
    if get_setting('attendance_enabled') != 'true':
        return
    recipients = get_admin_emails()
    if not recipients:
        return

    action_label = '入場' if action == 'checkin' else '退場'
    icon         = '🟢' if action == 'checkin' else '🔴'
    name         = worker.get('name', '—')
    company      = worker.get('company', '—')
    site_url     = get_setting('site_url')

    subject = f'【BuildeeMgr】{icon} {name}（{company}）が{action_label}しました'
    body_text = (
        f'{name}（{company}）が{action_label}しました。\n\n'
        f'時刻: {att_date} {time_str}\n'
        f'操作: {action_label}\n\n'
        f'確認: {site_url}/attendance'
    )
    body_html = mu._html_wrap(
        f'{icon} {action_label}通知',
        f'''<p><strong>{name}</strong>（{company}）が{action_label}しました。</p>
        <table>
          <tr><th>日付</th><td>{att_date}</td></tr>
          <tr><th>時刻</th><td><strong>{time_str}</strong></td></tr>
          <tr><th>操作</th><td><span class="badge" style="background:{'#dcfce7;color:#166534' if action=='checkin' else '#fef2f2;color:#dc2626'}">{action_label}</span></td></tr>
        </table>
        <p><a href="{site_url}/attendance" style="color:#f97316">→ 入退場ページで確認する</a></p>''',
        color='#3b82f6' if action == 'checkin' else '#ef4444'
    )
    msg = mu.MailMessage(recipients, subject, body_text, body_html)
    _send_async(msg, f'attendance_{action}', worker.get('id', ''))


# ==================================================================
#  Trigger 3: 資格期限アラート（日次バッチ）
# ==================================================================
def check_cert_expiry_and_notify():
    """
    資格期限が N 日以内の作業員を抽出してアラートメール送信。
    スケジューラ or /api/admin/run-daily-check から呼ぶ。
    """
    if get_setting('cert_expiry_enabled') != 'true':
        return 0
    recipients = get_admin_emails()
    if not recipients:
        return 0

    days_ahead = int(get_setting('cert_expiry_days', '30'))
    threshold  = (date.today() + timedelta(days=days_ahead)).isoformat()
    today_str  = date.today().isoformat()
    site_url   = get_setting('site_url')

    workers = db.get_workers()
    expiring = [
        w for w in workers
        if w.get('cert_expiry') and today_str <= w['cert_expiry'] <= threshold
    ]
    expired = [
        w for w in workers
        if w.get('cert_expiry') and w['cert_expiry'] < today_str
    ]

    if not expiring and not expired:
        log.info("[Notifier] cert_expiry: no alerts needed")
        return 0

    rows_expiring = ''.join(
        f"<tr><td>{w['name']}</td><td>{w.get('company','—')}</td>"
        f"<td>{w.get('job','—')}</td>"
        f"<td style='color:#c2410c;font-weight:600'>{w['cert_expiry']}</td></tr>"
        for w in sorted(expiring, key=lambda x: x['cert_expiry'])
    )
    rows_expired = ''.join(
        f"<tr><td>{w['name']}</td><td>{w.get('company','—')}</td>"
        f"<td>{w.get('job','—')}</td>"
        f"<td style='color:#dc2626;font-weight:700'>{w['cert_expiry']} ⚠️期限切れ</td></tr>"
        for w in sorted(expired, key=lambda x: x['cert_expiry'])
    )

    total = len(expiring) + len(expired)
    subject = f'【BuildeeMgr】⚠️ 資格期限アラート — {total}名要確認'
    body_html = mu._html_wrap(
        '資格期限アラート',
        f'''<p>本日 {today_str} 時点での資格期限確認レポートです。</p>
        {'<h3 style="color:#dc2626">🔴 期限切れ (' + str(len(expired)) + '名)</h3><table><tr><th>氏名</th><th>会社</th><th>職種</th><th>期限</th></tr>' + rows_expired + '</table>' if expired else ''}
        {'<h3 style="color:#c2410c">🟡 ' + str(days_ahead) + '日以内に期限切れ (' + str(len(expiring)) + '名)</h3><table><tr><th>氏名</th><th>会社</th><th>職種</th><th>期限</th></tr>' + rows_expiring + '</table>' if expiring else ''}
        <p><a href="{site_url}/safety" style="color:#f97316">→ 労務安全ページで確認する</a></p>''',
        color='#f97316'
    )
    body_text = (
        f'資格期限アラート ({today_str})\n\n'
        + (f'[期限切れ] {len(expired)}名\n' + '\n'.join(f"  - {w['name']}({w.get('company','')}) {w['cert_expiry']}" for w in expired) + '\n\n' if expired else '')
        + (f'[{days_ahead}日以内] {len(expiring)}名\n' + '\n'.join(f"  - {w['name']}({w.get('company','')}) {w['cert_expiry']}" for w in expiring) if expiring else '')
        + f'\n\n確認: {site_url}/safety'
    )
    msg = mu.MailMessage(recipients, subject, body_text, body_html)
    _send_async(msg, 'cert_expiry_alert')
    log.info(f"[Notifier] cert_expiry_alert: {total} workers notified")
    return total


# ==================================================================
#  Trigger 4: 日次サマリーレポート
# ==================================================================
def send_daily_report():
    """当日の入退場・KY・スケジュールのサマリーを朝8時に送信。"""
    if get_setting('daily_report_enabled') != 'true':
        return
    recipients = get_admin_emails()
    if not recipients:
        return

    today     = date.today().isoformat()
    site_url  = get_setting('site_url')
    stats     = db.get_dashboard_stats(today)

    workers_in   = stats.get('workers_in',   0)
    schedules    = stats.get('schedules',    0)
    ky_pending   = stats.get('ky_pending',   0)
    total_workers= stats.get('total_workers', 0)

    subject = f'【BuildeeMgr】日次レポート {today}'
    body_html = mu._html_wrap(
        f'日次レポート {today}',
        f'''<p>本日の現場状況サマリーです。</p>
        <table>
          <tr><th>現在入場中</th><td><strong style="font-size:18px">{workers_in}</strong> 名</td></tr>
          <tr><th>本日の作業予定</th><td>{schedules} 件</td></tr>
          <tr><th>KY未承認</th><td>{'<span style="color:#dc2626;font-weight:700">' + str(ky_pending) + ' 件</span>' if ky_pending else '0 件'}</td></tr>
          <tr><th>登録作業員総数</th><td>{total_workers} 名</td></tr>
        </table>
        <p><a href="{site_url}" style="color:#f97316">→ ダッシュボードを開く</a></p>''',
        color='#6366f1'
    )
    body_text = (
        f'日次レポート {today}\n\n'
        f'現在入場中  : {workers_in}名\n'
        f'本日作業予定: {schedules}件\n'
        f'KY未承認    : {ky_pending}件\n'
        f'登録作業員  : {total_workers}名\n\n'
        f'確認: {site_url}'
    )
    msg = mu.MailMessage(recipients, subject, body_text, body_html)
    _send_async(msg, 'daily_report')


# ==================================================================
#  Trigger 5: 管理者向けエラー通知
# ==================================================================
def notify_system_error(error_type: str, detail: str):
    """システムエラー発生時に管理者へ緊急通知。"""
    recipients = get_admin_emails()
    if not recipients:
        return

    subject = f'【BuildeeMgr】🚨 システムエラー: {error_type}'
    body_text = (
        f'BuildeeMgr でシステムエラーが発生しました。\n\n'
        f'種別: {error_type}\n'
        f'詳細: {detail}\n'
        f'発生時刻: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n\n'
        f'サーバーログを確認してください。'
    )
    body_html = mu._html_wrap(
        '🚨 システムエラー通知',
        f'''<p style="color:#dc2626;font-weight:700">システムエラーが発生しました。</p>
        <table>
          <tr><th>種別</th><td style="color:#dc2626">{error_type}</td></tr>
          <tr><th>詳細</th><td><pre style="font-size:12px;background:#fef2f2;padding:8px;border-radius:6px">{detail}</pre></td></tr>
          <tr><th>発生時刻</th><td>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td></tr>
        </table>
        <p style="color:#64748b;font-size:12px">サーバーログを確認してください。</p>''',
        color='#dc2626'
    )
    msg = mu.MailMessage(recipients, subject, body_text, body_html)
    _send_async(msg, 'system_error')


# ==================================================================
# ==================================================================
#  Daily scheduler (lightweight — no celery needed)
# ==================================================================
def start_daily_scheduler():
    """
    毎日指定時刻に日次タスクを実行するバックグラウンドスレッド。
    app.py の起動時に一度だけ呼ぶ。
    タスク:
      - 日次バックアップ
      - 毎週日曜に週次バックアップ
      - 毎月1日に月次バックアップ
      - 日次レポートメール
      - 資格期限アラートメール
    """
    import time
    import backup_utils as bu

    def _notify_backup(result: dict):
        """バックアップ結果をメール通知（失敗時は必ず、成功時は設定次第）。"""
        try:
            from mail_utils import MailMessage, send_mail, _html_wrap
            recipients = get_admin_emails()
            if not recipients:
                return
            if result['success']:
                if get_setting('backup_notify_success', 'false') != 'true':
                    return
                subject = f"【BuildeeMgr】✅ バックアップ完了 — {result.get('kind','')}"
                body_html = _html_wrap(
                    'バックアップ完了',
                    f'''<p><strong>{result["kind"]}</strong> バックアップが正常に完了しました。</p>
                    <table>
                      <tr><th>ファイル名</th><td>{result["filename"]}</td></tr>
                      <tr><th>サイズ</th><td>{result["size"]:,} bytes</td></tr>
                      <tr><th>SHA-256</th><td style="font-size:11px;font-family:monospace">{result["sha256"][:32]}…</td></tr>
                      <tr><th>所要時間</th><td>{result.get("duration_s",0):.1f} 秒</td></tr>
                      <tr><th>削除世代</th><td>{len(result.get("pruned",[]))} 件</td></tr>
                    </table>''',
                    color='#22c55e'
                )
            else:
                subject = f"【BuildeeMgr】🚨 バックアップ失敗 — {result.get('kind','')}"
                body_html = _html_wrap(
                    '🚨 バックアップ失敗',
                    f'''<p style="color:#dc2626">バックアップが失敗しました。至急確認してください。</p>
                    <table>
                      <tr><th>種別</th><td>{result.get("kind","")}</td></tr>
                      <tr><th>エラー</th><td style="color:#dc2626">{result.get("error","不明")}</td></tr>
                      <tr><th>日時</th><td>{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</td></tr>
                    </table>''',
                    color='#dc2626'
                )
            body_text = subject
            msg = MailMessage(recipients, subject, body_text, body_html)
            send_mail(msg)
        except Exception as e:
            log.error(f"[Scheduler] backup notify error: {e}")

    def _loop():
        last_run_date   = None
        last_run_weekly = None
        last_run_monthly= None

        while True:
            now        = datetime.now()
            run_hour   = int(get_setting('daily_report_hour', '8'))
            today      = now.date()
            today_str  = today.isoformat()

            if now.hour == run_hour and last_run_date != today_str:
                last_run_date = today_str
                log.info(f"[Scheduler] Running daily tasks at {now.strftime('%H:%M')}")

                # --- 日次バックアップ ---
                try:
                    result = bu.run_scheduled_backup(bu.KIND_DAILY)
                    _notify_backup(result)
                except Exception as e:
                    log.error(f"[Scheduler] daily backup error: {e}")

                # --- 週次バックアップ (日曜日) ---
                week_key = today.strftime('%Y-W%W')
                if today.weekday() == 6 and last_run_weekly != week_key:
                    last_run_weekly = week_key
                    try:
                        result = bu.run_scheduled_backup(bu.KIND_WEEKLY)
                        _notify_backup(result)
                    except Exception as e:
                        log.error(f"[Scheduler] weekly backup error: {e}")

                # --- 月次バックアップ (毎月1日) ---
                month_key = today.strftime('%Y-%m')
                if today.day == 1 and last_run_monthly != month_key:
                    last_run_monthly = month_key
                    try:
                        result = bu.run_scheduled_backup(bu.KIND_MONTHLY)
                        _notify_backup(result)
                    except Exception as e:
                        log.error(f"[Scheduler] monthly backup error: {e}")

                # --- 日次レポート・資格期限アラート ---
                try:
                    send_daily_report()
                    check_cert_expiry_and_notify()
                    # TLS証明書の期限確認（Let's Encrypt / 自己署名）
                    try:
                        from certbot_manager import check_and_notify_cert_expiry
                        check_and_notify_cert_expiry(
                            get_admin_emails(),
                            get_setting('site_url', 'https://localhost:5443')
                        )
                    except Exception as ce:
                        log.error(f"[Scheduler] cert expiry check error: {ce}")
                except Exception as e:
                    log.error(f"[Scheduler] daily task error: {e}")

            time.sleep(60)

    t = threading.Thread(target=_loop, daemon=True, name='daily_scheduler')
    t.start()
    log.info("[Scheduler] Daily scheduler started (backup + reports)")
