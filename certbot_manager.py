# certbot_manager.py -- BuildeeMgr Let's Encrypt 証明書管理
# 証明書状態確認・有効期限監視・Nginx リロード連携
import os, subprocess, logging, threading, json, sqlite3
from datetime import datetime, timezone, timedelta
from pathlib  import Path
from typing   import Optional

log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# パス定数
# ------------------------------------------------------------------
BASE_DIR     = Path(os.path.dirname(os.path.abspath(__file__)))
CERTS_DIR    = BASE_DIR / 'certs'            # 自己署名証明書
LE_CONF_DIR  = Path('/etc/letsencrypt')       # Let's Encrypt (Docker volume)
LE_LIVE_DIR  = LE_CONF_DIR / 'live'

SELF_CERT = CERTS_DIR / 'buildee.crt'
SELF_KEY  = CERTS_DIR / 'buildee.key'

# ------------------------------------------------------------------
# 証明書情報取得
# ------------------------------------------------------------------
def _load_cert_info(cert_path: Path) -> dict:
    """PEM証明書ファイルから有効期限・SANを取得。"""
    if not cert_path.exists():
        return {'exists': False, 'path': str(cert_path)}
    try:
        from cryptography import x509
        from cryptography.hazmat.primitives.asymmetric import rsa as _rsa
        data = cert_path.read_bytes()
        cert = x509.load_pem_x509_certificate(data)
        now  = datetime.now(timezone.utc)
        exp  = cert.not_valid_after_utc
        days = (exp - now).days
        try:
            san_ext = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName)
            sans    = [str(n.value) for n in san_ext.value]
        except Exception:
            sans = []
        return {
            'exists':      True,
            'path':        str(cert_path),
            'cn':          cert.subject.get_attributes_for_oid(
                               x509.oid.NameOID.COMMON_NAME)[0].value,
            'not_before':  cert.not_valid_before_utc.strftime('%Y-%m-%d'),
            'not_after':   exp.strftime('%Y-%m-%d'),
            'days_left':   days,
            'expired':     days < 0,
            'expiring':    0 <= days <= 30,
            'sans':        sans,
            'serial':      str(cert.serial_number)[:12],
        }
    except Exception as e:
        return {'exists': True, 'path': str(cert_path), 'error': str(e)}


def get_self_signed_info() -> dict:
    """自己署名証明書の情報を返す。"""
    return {**_load_cert_info(SELF_CERT), 'type': 'self_signed'}


def get_letsencrypt_domains() -> list[str]:
    """Let's Encrypt で管理されているドメイン一覧を返す。"""
    if not LE_LIVE_DIR.exists():
        return []
    return [d.name for d in LE_LIVE_DIR.iterdir() if d.is_dir() and d.name != 'README']


def get_letsencrypt_info(domain: str = '') -> dict:
    """指定ドメイン（省略時は最初のもの）の Let's Encrypt 証明書情報を返す。"""
    domains = get_letsencrypt_domains()
    if not domains:
        return {'exists': False, 'type': 'letsencrypt', 'domains': []}

    target = domain or domains[0]
    cert_path = LE_LIVE_DIR / target / 'fullchain.pem'
    info = _load_cert_info(cert_path)
    info['type']    = 'letsencrypt'
    info['domain']  = target
    info['domains'] = domains
    info['key_path']= str(LE_LIVE_DIR / target / 'privkey.pem')
    return info


def get_active_cert_info() -> dict:
    """現在 Nginx が使用している証明書の情報を返す（LE優先）。"""
    le_domains = get_letsencrypt_domains()
    if le_domains:
        info = get_letsencrypt_info(le_domains[0])
        info['active'] = True
        return info
    info = get_self_signed_info()
    info['active'] = True
    return info


def get_all_cert_status() -> dict:
    """管理画面用の全証明書ステータスをまとめて返す。"""
    return {
        'self_signed':  get_self_signed_info(),
        'letsencrypt':  get_letsencrypt_info(),
        'active':       get_active_cert_info(),
        'le_domains':   get_letsencrypt_domains(),
    }


# ------------------------------------------------------------------
# Nginx リロード
# ------------------------------------------------------------------
def reload_nginx() -> tuple[bool, str]:
    """
    Docker 環境: buildee_nginx コンテナに nginx -s reload を送る。
    直接起動環境: nginx -s reload を実行。
    """
    # Docker 環境
    try:
        result = subprocess.run(
            ['docker', 'exec', 'buildee_nginx', 'nginx', '-s', 'reload'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            log.info("[CertManager] Nginx reloaded via Docker exec")
            return True, 'Nginx リロード完了（Docker）'
        return False, result.stderr.strip()
    except FileNotFoundError:
        pass  # Docker が無い環境
    except Exception as e:
        log.warning(f"[CertManager] Docker reload failed: {e}")

    # 直接実行環境
    try:
        result = subprocess.run(
            ['nginx', '-s', 'reload'],
            capture_output=True, text=True, timeout=15
        )
        if result.returncode == 0:
            log.info("[CertManager] Nginx reloaded directly")
            return True, 'Nginx リロード完了'
        return False, result.stderr.strip()
    except FileNotFoundError:
        return False, 'Nginx が見つかりません（Docker 環境外では直接 reload してください）'
    except Exception as e:
        return False, str(e)


# ------------------------------------------------------------------
# certbot 実行
# ------------------------------------------------------------------
def run_certbot_renew(dry_run: bool = False) -> dict:
    """
    certbot renew を実行する。
    Docker 環境: buildee_certbot コンテナ内で実行
    非Docker環境: certbot コマンドを直接実行
    """
    cmd_base = ['certbot', 'renew', '--quiet']
    if dry_run:
        cmd_base.append('--dry-run')

    # Docker 環境
    try:
        result = subprocess.run(
            ['docker', 'exec', 'buildee_certbot'] + cmd_base,
            capture_output=True, text=True, timeout=120
        )
        success = result.returncode == 0
        out     = (result.stdout + result.stderr).strip()
        if success:
            log.info(f"[CertManager] certbot renew {'(dry-run) ' if dry_run else ''}OK")
            # 証明書が更新された場合 Nginx をリロード
            if not dry_run and 'No renewals were attempted' not in out:
                reload_nginx()
        return {
            'success':  success,
            'dry_run':  dry_run,
            'output':   out,
            'renewed':  success and 'No renewals were attempted' not in out,
            'source':   'docker',
        }
    except FileNotFoundError:
        pass
    except Exception as e:
        log.warning(f"[CertManager] Docker certbot failed: {e}")

    # 直接実行
    try:
        result = subprocess.run(
            cmd_base + ['--deploy-hook', 'nginx -s reload'],
            capture_output=True, text=True, timeout=120
        )
        success = result.returncode == 0
        return {
            'success': success,
            'dry_run': dry_run,
            'output':  (result.stdout + result.stderr).strip(),
            'renewed': success,
            'source':  'direct',
        }
    except FileNotFoundError:
        return {
            'success': False,
            'dry_run': dry_run,
            'output':  'certbot コマンドが見つかりません',
            'renewed': False,
            'source':  'none',
        }
    except Exception as e:
        return {'success': False, 'output': str(e), 'renewed': False}


def run_certbot_obtain(domain: str, email: str,
                       webroot: str = '/var/www/certbot',
                       staging: bool = False) -> dict:
    """
    新規ドメインの証明書を取得する。
    staging=True でレート制限を回避したテスト取得。
    """
    cmd = [
        'certbot', 'certonly',
        '--webroot', '--webroot-path', webroot,
        '--email', email,
        '--agree-tos', '--no-eff-email',
        '-d', domain,
    ]
    if staging:
        cmd.append('--staging')

    # Docker 環境
    try:
        result = subprocess.run(
            ['docker', 'exec', 'buildee_certbot'] + cmd,
            capture_output=True, text=True, timeout=180
        )
        success = result.returncode == 0
        if success:
            log.info(f"[CertManager] Certificate obtained for {domain}")
            _update_nginx_for_letsencrypt(domain)
            reload_nginx()
        return {
            'success': success,
            'domain':  domain,
            'output':  (result.stdout + result.stderr).strip(),
            'staging': staging,
        }
    except FileNotFoundError:
        return {'success': False, 'output': 'Docker が見つかりません', 'domain': domain}
    except Exception as e:
        return {'success': False, 'output': str(e), 'domain': domain}


def _update_nginx_for_letsencrypt(domain: str):
    """Nginx 設定の証明書パスを Let's Encrypt 用に切り替える。"""
    conf_path = BASE_DIR / 'nginx' / 'conf.d' / 'buildee.conf'
    if not conf_path.exists():
        return
    text = conf_path.read_text(encoding='utf-8')

    # 自己署名をコメントアウト、Let's Encrypt を有効化
    import re
    # ssl_certificate 行の切り替え
    text = re.sub(
        r'^(\s*)ssl_certificate\s+/etc/nginx/ssl/buildee\.crt;',
        r'\1# ssl_certificate /etc/nginx/ssl/buildee.crt;  # (自己署名 — LE取得後無効)',
        text, flags=re.MULTILINE
    )
    text = re.sub(
        r'^(\s*)ssl_certificate_key\s+/etc/nginx/ssl/buildee\.key;',
        r'\1# ssl_certificate_key /etc/nginx/ssl/buildee.key;  # (自己署名 — LE取得後無効)',
        text, flags=re.MULTILINE
    )
    text = re.sub(
        r'^(\s*)#\s*ssl_certificate\s+/etc/letsencrypt/live/.*?fullchain\.pem;',
        rf'\1ssl_certificate     /etc/letsencrypt/live/{domain}/fullchain.pem;',
        text, flags=re.MULTILINE
    )
    text = re.sub(
        r'^(\s*)#\s*ssl_certificate_key\s+/etc/letsencrypt/live/.*?privkey\.pem;',
        rf'\1ssl_certificate_key /etc/letsencrypt/live/{domain}/privkey.pem;',
        text, flags=re.MULTILINE
    )
    # server_name の切り替え
    text = re.sub(
        r'server_name\s+localhost;',
        f'server_name  {domain};',
        text
    )
    conf_path.write_text(text, encoding='utf-8')
    log.info(f"[CertManager] nginx conf updated for {domain}")


# ------------------------------------------------------------------
# 自動更新スケジューラ（notifier の日次スケジューラに相乗り）
# ------------------------------------------------------------------
def check_and_notify_cert_expiry(admin_emails: list[str], site_url: str) -> dict:
    """
    証明書期限確認 + アラートメール送信。
    notifier.py の日次タスクから呼ばれる。
    """
    info = get_active_cert_info()
    result = {'checked': True, 'info': info, 'notified': False}

    if not info.get('exists'):
        return result

    days = info.get('days_left', 999)
    if days > 30:
        return result  # 余裕あり

    if not admin_emails:
        return result

    try:
        from mail_utils import MailMessage, send_mail, _html_wrap
        cert_type = info.get('type', '不明')
        domain    = info.get('cn') or info.get('domain', 'localhost')

        if days < 0:
            subject = f'【BuildeeMgr】🚨 TLS証明書が期限切れです — {domain}'
            color   = '#dc2626'
            badge   = '<span style="background:#fef2f2;color:#dc2626;padding:2px 10px;border-radius:20px;font-weight:700">⚠️ 期限切れ</span>'
        else:
            subject = f'【BuildeeMgr】⚠️ TLS証明書が{days}日後に期限切れ — {domain}'
            color   = '#f97316'
            badge   = f'<span style="background:#fff7ed;color:#c2410c;padding:2px 10px;border-radius:20px;font-weight:700">残り{days}日</span>'

        body_html = _html_wrap(
            '🔒 TLS証明書 期限アラート',
            f'''<p>TLS証明書の期限が近づいています。</p>
            <table>
              <tr><th>ドメイン</th><td><strong>{domain}</strong></td></tr>
              <tr><th>種別</th><td>{"Let's Encrypt" if cert_type=="letsencrypt" else "自己署名"}</td></tr>
              <tr><th>有効期限</th><td>{info.get("not_after","—")}</td></tr>
              <tr><th>残り日数</th><td>{badge}</td></tr>
            </table>
            {"<p style='color:#22c55e'>Let's Encrypt 証明書は certbot により自動更新されます。</p>" if cert_type=='letsencrypt' else f"<p><a href='{site_url}/admin/users' style='color:#f97316'>→ 証明書を更新してください</a></p>"}
            ''',
            color=color
        )
        msg = MailMessage(admin_emails, subject, subject, body_html)
        ok, err = send_mail(msg)
        result['notified'] = ok
        if not ok and err != 'disabled':
            log.error(f"[CertManager] cert expiry notify failed: {err}")
    except Exception as e:
        log.error(f"[CertManager] notify error: {e}")

    return result


# ------------------------------------------------------------------
# 更新ログ（DB）
# ------------------------------------------------------------------
def init_cert_log_db():
    import database
    conn = sqlite3.connect(database.DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cert_renewal_log (
            id          TEXT PRIMARY KEY,
            action      TEXT NOT NULL,
            domain      TEXT,
            success     INTEGER NOT NULL,
            output      TEXT,
            renewed     INTEGER DEFAULT 0,
            dry_run     INTEGER DEFAULT 0,
            created_at  TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()

def log_cert_action(action: str, result: dict):
    import database, uuid
    try:
        conn = sqlite3.connect(database.DB_PATH)
        conn.execute("""
            INSERT INTO cert_renewal_log
            (id, action, domain, success, output, renewed, dry_run)
            VALUES (?,?,?,?,?,?,?)
        """, (
            str(uuid.uuid4()), action,
            result.get('domain', ''),
            1 if result.get('success') else 0,
            (result.get('output') or '')[:2000],
            1 if result.get('renewed') else 0,
            1 if result.get('dry_run') else 0,
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        log.error(f"[CertManager] log_cert_action failed: {e}")

def get_cert_renewal_log(limit: int = 30) -> list:
    import database
    try:
        conn = sqlite3.connect(database.DB_PATH)
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            "SELECT * FROM cert_renewal_log ORDER BY created_at DESC LIMIT ?",
            (limit,)
        ).fetchall()
        conn.close()
        return [dict(r) for r in rows]
    except Exception:
        return []
