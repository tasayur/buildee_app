# config.py -- BuildeeMgr environment configuration
import os

def _env(key, default=''):   return os.environ.get(key, default)
def _bool(key, default=False):
    v = os.environ.get(key,'').lower()
    if v in ('1','true','yes'):  return True
    if v in ('0','false','no'):  return False
    return default
def _int(key, default=0):
    try:    return int(os.environ.get(key, default))
    except: return default

def load_dotenv(path='.env'):
    if not os.path.exists(path): return
    with open(path, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#') or '=' not in line: continue
            key, _, val = line.partition('=')
            key = key.strip(); val = val.strip().strip('"').strip("'")
            if key and key not in os.environ: os.environ[key] = val

load_dotenv()

class Config:
    # Flask
    SECRET_KEY = _env('SECRET_KEY', 'buildee-change-me-in-production-2024')
    DEBUG      = _bool('FLASK_DEBUG', False)

    # HTTPS
    HTTPS_ENABLED   = _bool('HTTPS_ENABLED', True)
    HTTPS_PORT      = _int('HTTPS_PORT',  5443)
    HTTP_PORT       = _int('HTTP_PORT',   5000)
    HTTP_REDIRECT   = _bool('HTTP_REDIRECT', True)
    CERT_FILE       = _env('CERT_FILE',  '')
    KEY_FILE        = _env('KEY_FILE',   '')

    # Security headers
    HSTS_MAX_AGE    = _int('HSTS_MAX_AGE', 31536000)
    HSTS_SUBDOMAINS = _bool('HSTS_SUBDOMAINS', False)

    # Session
    SESSION_COOKIE_SECURE   = _bool('SESSION_COOKIE_SECURE',   True)
    SESSION_COOKIE_HTTPONLY = _bool('SESSION_COOKIE_HTTPONLY',  True)
    SESSION_COOKIE_SAMESITE = _env('SESSION_COOKIE_SAMESITE',  'Lax')
    PERMANENT_SESSION_LIFETIME = _int('SESSION_LIFETIME_DAYS', 7) * 86400

    # DB
    DB_PATH = _env('DB_PATH', '')

    # ---- Mail / SMTP ----
    MAIL_ENABLED   = _bool('MAIL_ENABLED',  False)
    SMTP_HOST      = _env('SMTP_HOST',      'smtp.gmail.com')
    SMTP_PORT      = _int('SMTP_PORT',      587)
    SMTP_USER      = _env('SMTP_USER',      '')
    SMTP_PASSWORD  = _env('SMTP_PASSWORD',  '')
    SMTP_FROM      = _env('SMTP_FROM',      '')
    SMTP_USE_TLS   = _bool('SMTP_USE_TLS',  True)
    SMTP_USE_SSL   = _bool('SMTP_USE_SSL',  False)

    @classmethod
    def summary(cls):
        lines = [
            f"  HTTPS:        {'enabled' if cls.HTTPS_ENABLED else 'disabled'}",
            f"  HTTPS port:   {cls.HTTPS_PORT}",
            f"  HTTP port:    {cls.HTTP_PORT}",
            f"  HTTP→HTTPS:   {'yes' if cls.HTTP_REDIRECT else 'no'}",
            f"  Debug:        {'yes' if cls.DEBUG else 'no'}",
            f"  Secure cookie:{'yes' if cls.SESSION_COOKIE_SECURE else 'no'}",
            f"  Mail:         {'enabled (' + cls.SMTP_HOST + ')' if cls.MAIL_ENABLED else 'disabled'}",
        ]
        return '\n'.join(lines)
