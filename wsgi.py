# wsgi.py -- Gunicorn / uWSGI エントリーポイント
#
# 起動例:
#   gunicorn --bind 0.0.0.0:5000 --workers 2 --threads 4 wsgi:app
#
# Nginx リバースプロキシ下で X-Forwarded-* を正しく処理するため
# ProxyFix ミドルウェアを適用する。
from werkzeug.middleware.proxy_fix import ProxyFix
from app import app

# x_for=1: X-Forwarded-For  1段のプロキシ (Nginx のみ)
# x_proto=1: X-Forwarded-Proto (HTTP/HTTPS 判定に使用)
# x_host=1: X-Forwarded-Host
app.wsgi_app = ProxyFix(
    app.wsgi_app,
    x_for=1,
    x_proto=1,
    x_host=1,
    x_prefix=1,
)

if __name__ == '__main__':
    app.run()
