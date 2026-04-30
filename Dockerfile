# ================================================================
#  Dockerfile -- BuildeeMgr  (マルチステージビルド)
#  Stage 1: builder  依存パッケージをコンパイル
#  Stage 2: runtime  最小イメージ（~180MB）
# ================================================================

# ---- Stage 1: builder ----
FROM python:3.12-slim AS builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libffi-dev libssl-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY requirements.txt .
RUN pip install --no-cache-dir --prefix=/install -r requirements.txt gunicorn


# ---- Stage 2: runtime ----
FROM python:3.12-slim

# ランタイム依存のみ
RUN apt-get update && apt-get install -y --no-install-recommends \
    libssl3 libffi8 \
    && rm -rf /var/lib/apt/lists/* \
    # セキュリティ: 非rootユーザー作成
    && useradd -r -u 1001 -s /bin/false appuser

# builder からパッケージをコピー
COPY --from=builder /install /usr/local

WORKDIR /app

# アプリコードをコピー（.dockerignore で除外済みのものは含まれない）
COPY --chown=appuser:appuser . .

# 永続化ディレクトリ作成
RUN mkdir -p /app/data /app/backups /app/certs /app/static \
    && chown -R appuser:appuser /app

# DB パスをコンテナ用に上書き（volume マウント先）
ENV DB_PATH=/app/data/buildee.db \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    FLASK_APP=wsgi:app

# 非rootユーザーで実行
USER appuser

EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
    CMD python -c \
    "import urllib.request,sys; \
     r=urllib.request.urlopen('http://localhost:5000/offline',timeout=5); \
     sys.exit(0 if r.status==200 else 1)"

# Gunicorn: CPU*2+1 ワーカー、スレッド4
CMD ["gunicorn", \
     "--config", "gunicorn.conf.py", \
     "wsgi:app"]
