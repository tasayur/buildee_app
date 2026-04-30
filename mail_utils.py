# mail_utils.py -- BuildeeMgr SMTP メール送信エンジン
# 対応: Gmail / Outlook / SendGrid / 社内SMTPサーバー
import smtplib, ssl, uuid, logging
from email.mime.multipart import MIMEMultipart
from email.mime.text      import MIMEText
from email.utils          import formatdate, make_msgid
from datetime             import datetime
from typing               import Optional, List
import config as cfg

log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# Config helpers
# ------------------------------------------------------------------
def _c(key, default=''):
    """Read mail config from Config or fallback."""
    return getattr(cfg.Config, key, default) or default

class MailConfig:
    SMTP_HOST     = _c('SMTP_HOST',     'smtp.gmail.com')
    SMTP_PORT     = int(_c('SMTP_PORT', '587'))
    SMTP_USER     = _c('SMTP_USER',     '')
    SMTP_PASSWORD = _c('SMTP_PASSWORD', '')
    SMTP_FROM     = _c('SMTP_FROM',     '')
    SMTP_USE_TLS  = str(_c('SMTP_USE_TLS',  'true')).lower() != 'false'
    SMTP_USE_SSL  = str(_c('SMTP_USE_SSL',  'false')).lower() == 'true'
    MAIL_ENABLED  = str(_c('MAIL_ENABLED',  'false')).lower() == 'true'

    @classmethod
    def refresh(cls):
        """Reload from config (call after .env changes)."""
        cls.SMTP_HOST     = _c('SMTP_HOST',     'smtp.gmail.com')
        cls.SMTP_PORT     = int(_c('SMTP_PORT', '587'))
        cls.SMTP_USER     = _c('SMTP_USER',     '')
        cls.SMTP_PASSWORD = _c('SMTP_PASSWORD', '')
        cls.SMTP_FROM     = _c('SMTP_FROM',     '')
        cls.SMTP_USE_TLS  = str(_c('SMTP_USE_TLS', 'true')).lower() != 'false'
        cls.SMTP_USE_SSL  = str(_c('SMTP_USE_SSL', 'false')).lower() == 'true'
        cls.MAIL_ENABLED  = str(_c('MAIL_ENABLED', 'false')).lower() == 'true'

    @classmethod
    def is_configured(cls):
        return bool(cls.SMTP_USER and cls.SMTP_PASSWORD and cls.SMTP_FROM)

    @classmethod
    def summary(cls):
        return {
            'enabled':  cls.MAIL_ENABLED,
            'host':     cls.SMTP_HOST,
            'port':     cls.SMTP_PORT,
            'user':     cls.SMTP_USER,
            'from':     cls.SMTP_FROM,
            'use_tls':  cls.SMTP_USE_TLS,
            'use_ssl':  cls.SMTP_USE_SSL,
            'configured': cls.is_configured(),
        }


# ------------------------------------------------------------------
# Low-level send
# ------------------------------------------------------------------
class MailMessage:
    def __init__(self, to: List[str], subject: str,
                 body_text: str = '', body_html: str = '',
                 reply_to: str = ''):
        self.to        = to if isinstance(to, list) else [to]
        self.subject   = subject
        self.body_text = body_text
        self.body_html = body_html
        self.reply_to  = reply_to
        self.message_id = make_msgid(domain='buildee.local')


def send_mail(msg: MailMessage) -> tuple[bool, str]:
    """
    Send a MailMessage via SMTP.
    Returns (success: bool, error_message: str).
    """
    # refresh() は起動時・設定変更時に呼ぶこと（send_mail ループ内では呼ばない）

    if not MailConfig.MAIL_ENABLED:
        log.info(f"[Mail] DISABLED — skipping: {msg.subject}")
        return True, 'disabled'

    if not MailConfig.is_configured():
        return False, 'SMTP 設定が不完全です（SMTP_USER / SMTP_PASSWORD / SMTP_FROM を .env に設定してください）'

    try:
        mime = MIMEMultipart('alternative')
        mime['Subject']    = msg.subject
        mime['From']       = MailConfig.SMTP_FROM
        mime['To']         = ', '.join(msg.to)
        mime['Date']       = formatdate(localtime=True)
        mime['Message-ID'] = msg.message_id
        if msg.reply_to:
            mime['Reply-To'] = msg.reply_to

        if msg.body_text:
            mime.attach(MIMEText(msg.body_text, 'plain', 'utf-8'))
        if msg.body_html:
            mime.attach(MIMEText(msg.body_html, 'html', 'utf-8'))
        elif msg.body_text:
            pass  # text only is fine
        else:
            return False, '本文が空です'

        context = ssl.create_default_context()

        if MailConfig.SMTP_USE_SSL:
            # Port 465 — direct SSL
            with smtplib.SMTP_SSL(MailConfig.SMTP_HOST, MailConfig.SMTP_PORT,
                                  context=context, timeout=15) as server:
                server.login(MailConfig.SMTP_USER, MailConfig.SMTP_PASSWORD)
                server.sendmail(MailConfig.SMTP_FROM, msg.to, mime.as_string())
        else:
            # Port 587 — STARTTLS
            with smtplib.SMTP(MailConfig.SMTP_HOST, MailConfig.SMTP_PORT,
                              timeout=15) as server:
                server.ehlo()
                if MailConfig.SMTP_USE_TLS:
                    server.starttls(context=context)
                    server.ehlo()
                server.login(MailConfig.SMTP_USER, MailConfig.SMTP_PASSWORD)
                server.sendmail(MailConfig.SMTP_FROM, msg.to, mime.as_string())

        log.info(f"[Mail] Sent: '{msg.subject}' → {msg.to}")
        return True, ''

    except smtplib.SMTPAuthenticationError:
        err = 'SMTP認証エラー: ユーザー名またはパスワードが正しくありません'
        log.error(f"[Mail] {err}")
        return False, err
    except smtplib.SMTPConnectError as e:
        err = f'SMTP接続エラー: {MailConfig.SMTP_HOST}:{MailConfig.SMTP_PORT} に接続できません'
        log.error(f"[Mail] {err} — {e}")
        return False, err
    except smtplib.SMTPRecipientsRefused as e:
        err = f'宛先エラー: {e.recipients}'
        log.error(f"[Mail] {err}")
        return False, err
    except TimeoutError:
        err = f'SMTP接続タイムアウト: {MailConfig.SMTP_HOST}'
        log.error(f"[Mail] {err}")
        return False, err
    except Exception as e:
        err = f'送信エラー: {str(e)}'
        log.error(f"[Mail] {err}")
        return False, err


def send_test_mail(to: str) -> tuple[bool, str]:
    """テストメールを送信する（管理画面から呼ぶ）。"""
    msg = MailMessage(
        to=[to],
        subject='【BuildeeMgr】メール送信テスト',
        body_text=(
            'BuildeeMgr からのテストメールです。\n\n'
            'このメールが届いていれば SMTP 設定は正常です。\n\n'
            f'送信日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}\n'
            '---\nBuildee 施工管理システム'
        ),
        body_html=_html_wrap(
            '✅ メール送信テスト',
            f'<p>BuildeeMgr からのテストメールです。</p>'
            f'<p>このメールが届いていれば <strong>SMTP 設定は正常</strong>です。</p>'
            f'<p style="color:#64748b;font-size:12px">送信日時: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}</p>',
            color='#22c55e'
        )
    )
    return send_mail(msg)


# ------------------------------------------------------------------
# HTML template helper
# ------------------------------------------------------------------
def _html_wrap(title: str, body: str, color: str = '#f97316') -> str:
    return f"""<!DOCTYPE html>
<html lang="ja"><head><meta charset="UTF-8">
<style>
  body{{font-family:'Hiragino Sans','Segoe UI',sans-serif;background:#f1f5f9;margin:0;padding:20px}}
  .card{{max-width:560px;margin:0 auto;background:#fff;border-radius:16px;overflow:hidden;
         box-shadow:0 4px 20px rgba(0,0,0,.08)}}
  .hdr{{background:{color};color:#fff;padding:20px 28px}}
  .hdr h1{{margin:0;font-size:18px;font-weight:700}}
  .hdr p{{margin:4px 0 0;font-size:13px;opacity:.85}}
  .body{{padding:24px 28px;color:#1e293b;font-size:14px;line-height:1.7}}
  .footer{{padding:14px 28px;background:#f8fafc;border-top:1px solid #e2e8f0;
           font-size:11px;color:#94a3b8;text-align:center}}
  .badge{{display:inline-block;padding:2px 10px;border-radius:20px;font-size:12px;font-weight:600}}
  table{{width:100%;border-collapse:collapse;margin:12px 0}}
  th{{background:#f8fafc;padding:8px 12px;text-align:left;font-size:12px;color:#64748b;border-bottom:1px solid #e2e8f0}}
  td{{padding:8px 12px;font-size:13px;border-bottom:1px solid #f1f5f9}}
</style></head>
<body><div class="card">
  <div class="hdr"><h1>🏗 {title}</h1><p>BuildeeMgr 施工管理システム</p></div>
  <div class="body">{body}</div>
  <div class="footer">このメールは BuildeeMgr から自動送信されています。返信不要です。</div>
</div></body></html>"""
