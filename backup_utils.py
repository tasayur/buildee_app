# backup_utils.py -- BuildeeMgr バックアップエンジン
# 世代管理・SHA-256整合性・SQLiteオンラインバックアップ・復元対応
import os, zipfile, sqlite3, hashlib, json, shutil, logging, uuid, re
from datetime import datetime, date
from pathlib  import Path
from typing   import List, Optional

log = logging.getLogger(__name__)

# ------------------------------------------------------------------
# 設定
# ------------------------------------------------------------------
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))

# Docker: バックアップをボリュームマウント先に保存
BACKUP_DIR = Path(os.environ.get('BACKUP_DIR', str(BASE_DIR / 'backups')))

# 世代保持数
KEEP_DAILY   = 7    # 直近7日分
KEEP_WEEKLY  = 4    # 直近4週分（日曜日）
KEEP_MONTHLY = 3    # 直近3ヶ月分（1日）

# バックアップ対象ファイル（相対パス）
BACKUP_TARGETS = [
    'buildee.db',
    '.env',
    'config.py',
    'certs/buildee.crt',
    'certs/buildee.key',
]
BACKUP_DIRS = [
    # ('ディレクトリ', 除外パターンリスト)
    # 'static/uploads' など将来のアップロードフォルダに対応
]

# バックアップ種別
KIND_MANUAL  = 'manual'
KIND_DAILY   = 'daily'
KIND_WEEKLY  = 'weekly'
KIND_MONTHLY = 'monthly'

# ------------------------------------------------------------------
# ユーティリティ
# ------------------------------------------------------------------
def _sha256(path: Path, chunk: int = 65536) -> str:
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        while True:
            buf = f.read(chunk)
            if not buf:
                break
            h.update(buf)
    return h.hexdigest()

def _safe_copy(src: Path, dst_dir: Path, arcname: str = None) -> Optional[str]:
    """ファイルを dst_dir にコピー。arcname でZIP内パスを指定。"""
    if not src.exists():
        log.warning(f"[Backup] skip (not found): {src}")
        return None
    return arcname or str(src.relative_to(BASE_DIR))

def _sqlite_online_backup(src_db: Path, dst_db: Path):
    """
    SQLite Online Backup API を使用。
    書き込み中のDBを安全にコピーできる（WALモード対応）。
    """
    src = sqlite3.connect(str(src_db))
    dst = sqlite3.connect(str(dst_db))
    try:
        src.backup(dst)
    finally:
        dst.close()
        src.close()

# ------------------------------------------------------------------
# バックアップ作成
# ------------------------------------------------------------------
def create_backup(kind: str = KIND_MANUAL, label: str = '') -> dict:
    """
    バックアップZIPを作成して backups/ に保存する。

    Returns:
        {
          'success': bool,
          'path': str,          # ZIPファイルの絶対パス
          'filename': str,
          'size': int,
          'sha256': str,
          'timestamp': str,
          'kind': str,
          'files': [str],       # ZIP内のファイル一覧
          'error': str,         # エラー時のみ
        }
    """
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    ts  = datetime.now().strftime('%Y%m%d_%H%M%S')
    tag = f"_{label}" if label else ''
    filename = f"buildee_{kind}_{ts}{tag}.zip"
    zip_path = BACKUP_DIR / filename
    meta_path = BACKUP_DIR / f"{filename}.meta.json"

    db_tmp   = None
    files_in = []

    try:
        with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED, compresslevel=6) as zf:

            # ---- 1. SQLite DB (Online Backup) ----
            db_src = BASE_DIR / 'buildee.db'
            if db_src.exists():
                db_tmp = zip_path.parent / f"_tmp_{ts}.db"
                _sqlite_online_backup(db_src, db_tmp)
                zf.write(db_tmp, 'buildee.db')
                files_in.append('buildee.db')

            # ---- 2. 個別ファイル ----
            for rel in BACKUP_TARGETS:
                src = BASE_DIR / rel
                if src.exists() and src != db_src:
                    zf.write(src, rel)
                    files_in.append(rel)

            # ---- 3. ディレクトリ ----
            for dir_rel, excludes in BACKUP_DIRS:
                dir_path = BASE_DIR / dir_rel
                if not dir_path.exists():
                    continue
                for fp in sorted(dir_path.rglob('*')):
                    if not fp.is_file():
                        continue
                    if any(re.search(ex, str(fp)) for ex in excludes):
                        continue
                    arcname = str(fp.relative_to(BASE_DIR))
                    zf.write(fp, arcname)
                    files_in.append(arcname)

        # ---- 整合性チェック ----
        sha = _sha256(zip_path)
        size = zip_path.stat().st_size

        # ---- メタデータ ----
        meta = {
            'filename':  filename,
            'kind':      kind,
            'timestamp': ts,
            'size':      size,
            'sha256':    sha,
            'files':     files_in,
            'label':     label,
        }
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding='utf-8')

        log.info(f"[Backup] Created: {filename} ({size:,}B) sha256={sha[:12]}…")
        return {'success': True, 'path': str(zip_path), 'filename': filename,
                'size': size, 'sha256': sha, 'timestamp': ts,
                'kind': kind, 'files': files_in}

    except Exception as e:
        log.error(f"[Backup] FAILED: {e}")
        if zip_path.exists():
            zip_path.unlink()
        return {'success': False, 'error': str(e), 'kind': kind, 'timestamp': ts}

    finally:
        if db_tmp and db_tmp.exists():
            db_tmp.unlink()


# ------------------------------------------------------------------
# 世代管理（古いバックアップを自動削除）
# ------------------------------------------------------------------
def _parse_ts(filename: str) -> Optional[datetime]:
    """buildee_KIND_YYYYMMDD_HHMMSS.zip からタイムスタンプを抽出。"""
    m = re.search(r'(\d{8}_\d{6})', filename)
    if m:
        try:
            return datetime.strptime(m.group(1), '%Y%m%d_%H%M%S')
        except ValueError:
            pass
    return None

def _list_backups_of_kind(kind: str) -> List[Path]:
    if not BACKUP_DIR.exists():
        return []
    zips = sorted(
        [p for p in BACKUP_DIR.glob(f'buildee_{kind}_*.zip') if not p.suffix == '.json'],
        key=lambda p: p.stat().st_mtime
    )
    return zips

def prune_old_backups():
    """世代管理: 各 kind ごとに保持数を超えた古いファイルを削除。"""
    rules = {
        KIND_DAILY:   KEEP_DAILY,
        KIND_WEEKLY:  KEEP_WEEKLY,
        KIND_MONTHLY: KEEP_MONTHLY,
        KIND_MANUAL:  10,   # 手動は10世代保持
    }
    removed = []
    for kind, keep in rules.items():
        zips = _list_backups_of_kind(kind)
        to_del = zips[:-keep] if len(zips) > keep else []
        for p in to_del:
            try:
                p.unlink()
                meta = p.parent / f"{p.name}.meta.json"
                if meta.exists():
                    meta.unlink()
                removed.append(p.name)
                log.info(f"[Backup] Pruned: {p.name}")
            except Exception as e:
                log.warning(f"[Backup] Prune failed: {p.name} — {e}")
    return removed


# ------------------------------------------------------------------
# バックアップ一覧
# ------------------------------------------------------------------
def list_backups() -> List[dict]:
    """backups/ 内の全ZIPを新しい順で返す。"""
    if not BACKUP_DIR.exists():
        return []
    results = []
    for p in sorted(BACKUP_DIR.glob('buildee_*.zip'),
                    key=lambda x: x.stat().st_mtime, reverse=True):
        meta_path = p.parent / f"{p.name}.meta.json"
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding='utf-8'))
                meta['path'] = str(p)
                meta['exists'] = True
                results.append(meta)
                continue
            except Exception:
                pass
        # メタなし → 最小情報を生成
        ts = _parse_ts(p.name)
        m  = re.search(r'buildee_(\w+)_', p.name)
        results.append({
            'filename':  p.name,
            'kind':      m.group(1) if m else 'unknown',
            'timestamp': ts.strftime('%Y%m%d_%H%M%S') if ts else '',
            'size':      p.stat().st_size,
            'sha256':    '',
            'files':     [],
            'path':      str(p),
            'exists':    True,
        })
    return results

def get_backup_stats() -> dict:
    """バックアップ統計を返す。"""
    items = list_backups()
    total_size = sum(i.get('size', 0) for i in items)
    by_kind = {}
    for i in items:
        k = i.get('kind','unknown')
        by_kind[k] = by_kind.get(k, 0) + 1
    latest = items[0] if items else None
    return {
        'total':      len(items),
        'total_size': total_size,
        'by_kind':    by_kind,
        'latest':     latest,
        'backup_dir': str(BACKUP_DIR),
    }


# ------------------------------------------------------------------
# 整合性検証
# ------------------------------------------------------------------
def verify_backup(filename: str) -> dict:
    """SHA-256 でバックアップの整合性を確認する。"""
    p = BACKUP_DIR / filename
    if not p.exists():
        return {'valid': False, 'error': 'ファイルが見つかりません'}

    # メタデータから期待ハッシュを取得
    meta_path = p.parent / f"{filename}.meta.json"
    expected_sha = ''
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text(encoding='utf-8'))
            expected_sha = meta.get('sha256', '')
        except Exception:
            pass

    actual_sha = _sha256(p)

    # ZIPの内部整合性チェック
    zip_ok = False
    bad_file = None
    try:
        with zipfile.ZipFile(p, 'r') as zf:
            bad_file = zf.testzip()
        zip_ok = (bad_file is None)
    except zipfile.BadZipFile as e:
        return {'valid': False, 'error': f'ZIPファイルが破損しています: {e}',
                'sha256': actual_sha}

    result = {
        'valid':        zip_ok and (not expected_sha or actual_sha == expected_sha),
        'sha256':       actual_sha,
        'sha256_match': (actual_sha == expected_sha) if expected_sha else None,
        'zip_ok':       zip_ok,
        'bad_file':     bad_file,
        'size':         p.stat().st_size,
        'filename':     filename,
    }
    return result


# ------------------------------------------------------------------
# 復元
# ------------------------------------------------------------------
def restore_backup(filename: str, targets: List[str] = None) -> dict:
    """
    バックアップZIPからファイルを復元する。
    targets=None の場合はDBのみ復元（安全のため）。
    targets=['buildee.db', '.env'] のように指定可能。
    """
    p = BACKUP_DIR / filename
    if not p.exists():
        return {'success': False, 'error': 'バックアップファイルが見つかりません'}

    # 復元前に現状をバックアップ
    pre = create_backup(KIND_MANUAL, 'before_restore')
    restored = []
    errors   = []

    try:
        with zipfile.ZipFile(p, 'r') as zf:
            names = zf.namelist()

            # デフォルト: DBのみ
            if targets is None:
                targets = ['buildee.db']

            for target in targets:
                if target not in names:
                    errors.append(f'{target}: ZIPに含まれていません')
                    continue

                dst = BASE_DIR / target
                dst.parent.mkdir(parents=True, exist_ok=True)

                # DBは専用処理
                # DBは専用処理 (read → tmp → move でロックを回避)
                if target == 'buildee.db':
                    tmp = BASE_DIR / f'_restore_tmp_{uuid.uuid4().hex[:8]}.db'
                    try:
                        # ZIPから一旦 tmp に展開
                        tmp.write_bytes(zf.read(target))
                        # WAL/SHM があれば先に削除
                        for ext in ['-wal', '-shm']:
                            wp = Path(str(dst) + ext)
                            if wp.exists():
                                wp.unlink()
                        shutil.move(str(tmp), str(dst))
                        restored.append(target)
                    except Exception as e:
                        errors.append(f'{target}: {e}')
                    finally:
                        if tmp.exists():
                            tmp.unlink()
                else:
                    try:
                        data = zf.read(target)
                        dst.write_bytes(data)
                        restored.append(target)
                    except Exception as e:
                        errors.append(f'{target}: {e}')

        log.info(f"[Backup] Restored from {filename}: {restored}")
        return {
            'success':          True,
            'restored':         restored,
            'errors':           errors,
            'pre_backup':       pre.get('filename', ''),
            'source':           filename,
        }

    except Exception as e:
        log.error(f"[Backup] Restore failed: {e}")
        return {'success': False, 'error': str(e), 'pre_backup': pre.get('filename', '')}


# ------------------------------------------------------------------
# バックアップログ（DB内テーブル）
# ------------------------------------------------------------------
def init_backup_db():
    """バックアップ実行履歴テーブルを作成。"""
    import database
    conn = sqlite3.connect(database.DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS backup_log (
            id         TEXT PRIMARY KEY,
            kind       TEXT NOT NULL,
            filename   TEXT,
            size       INTEGER,
            sha256     TEXT,
            success    INTEGER NOT NULL,
            error_msg  TEXT,
            duration_s REAL,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    """)
    conn.commit()
    conn.close()

def log_backup_result(result: dict, duration_s: float = 0.0):
    """バックアップ結果をDBに記録。"""
    import database
    conn = sqlite3.connect(database.DB_PATH)
    conn.execute("""
        INSERT INTO backup_log
        (id, kind, filename, size, sha256, success, error_msg, duration_s)
        VALUES (?,?,?,?,?,?,?,?)
    """, (
        str(uuid.uuid4()),
        result.get('kind', ''),
        result.get('filename', ''),
        result.get('size', 0),
        result.get('sha256', ''),
        1 if result.get('success') else 0,
        result.get('error', ''),
        round(duration_s, 2),
    ))
    conn.commit()
    conn.close()

def get_backup_log(limit: int = 30) -> List[dict]:
    import database
    conn = sqlite3.connect(database.DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM backup_log ORDER BY created_at DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ------------------------------------------------------------------
# スケジューラ用エントリーポイント
# ------------------------------------------------------------------
def run_scheduled_backup(kind: str = KIND_DAILY) -> dict:
    """スケジューラから呼ぶメイン関数。バックアップ→世代管理→ログ記録。"""
    import time
    t0 = time.monotonic()
    result = create_backup(kind)
    duration = time.monotonic() - t0
    pruned = prune_old_backups()
    log_backup_result(result, duration)
    result['pruned'] = pruned
    result['duration_s'] = round(duration, 2)
    return result
