# gunicorn.conf.py  --  BuildeeMgr Gunicorn 設定
# Docker / 本番サーバー共通
import multiprocessing, os

# ---- バインド ----
bind    = "0.0.0.0:5000"
backlog = 512

# ---- ワーカー ----
# Docker では CPU 数が限定されることが多いため上限4に制限
_cpu = multiprocessing.cpu_count()
workers      = min(_cpu * 2 + 1, 4)
worker_class = "sync"
threads      = 4
worker_connections = 1000

# ---- タイムアウト ----
timeout          = 60     # Excel出力・バックアップ等に余裕
graceful_timeout = 30
keepalive        = 5

# ---- セキュリティ ----
limit_request_line    = 8190
limit_request_fields  = 200
forwarded_allow_ips   = "127.0.0.1,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

# ---- ログ (コンテナ対応: stdout/stderr) ----
accesslog  = "-"
errorlog   = "-"
loglevel   = os.getenv("LOG_LEVEL", "info")
access_log_format = '%(h)s "%(r)s" %(s)s %(b)s %(D)sms'

# ---- プロセス名 ----
proc_name = "buildee_mgr"

def on_starting(server):
    print(f"[Gunicorn] BuildeeMgr starting (workers={workers}, threads={threads})")

def worker_exit(server, worker):
    print(f"[Gunicorn] Worker {worker.pid} exited")
