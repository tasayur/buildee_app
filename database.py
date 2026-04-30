# database.py -- BuildeeMgr SQLite persistence layer
import sqlite3
import os
from datetime import datetime, date, timedelta

# DB_PATH: 環境変数 DB_PATH → デフォルト（アプリ隣のbuildee.db）
# Docker コンテナでは DB_PATH=/app/data/buildee.db を設定
DB_PATH = os.environ.get('DB_PATH') or \
          os.path.join(os.path.dirname(os.path.abspath(__file__)), 'buildee.db')

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

# ------------------------------------------------------------------
# Schema
# ------------------------------------------------------------------
SCHEMA = """
CREATE TABLE IF NOT EXISTS companies (
    id         TEXT PRIMARY KEY,
    name       TEXT NOT NULL,
    type       TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS work_schedules (
    id            TEXT PRIMARY KEY,
    date          TEXT NOT NULL,
    company       TEXT NOT NULL,
    work_content  TEXT NOT NULL,
    location      TEXT,
    workers_count INTEGER DEFAULT 1,
    time_start    TEXT,
    time_end      TEXT,
    note          TEXT,
    status        TEXT DEFAULT 'scheduled',
    created_at    TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_ws_date ON work_schedules(date);

CREATE TABLE IF NOT EXISTS equipment_reservations (
    id          TEXT PRIMARY KEY,
    date        TEXT NOT NULL,
    equipment   TEXT NOT NULL,
    company     TEXT NOT NULL,
    time_start  TEXT NOT NULL,
    time_end    TEXT NOT NULL,
    purpose     TEXT,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_eq_date ON equipment_reservations(date);

CREATE TABLE IF NOT EXISTS ky_records (
    id           TEXT PRIMARY KEY,
    date         TEXT NOT NULL,
    company      TEXT NOT NULL,
    work_content TEXT NOT NULL,
    danger_point TEXT,
    measure      TEXT,
    check_method TEXT,
    level        TEXT DEFAULT 'medium',
    signer       TEXT,
    status       TEXT DEFAULT '未承認',
    approved_at  TEXT,
    created_at   TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_ky_date   ON ky_records(date);
CREATE INDEX IF NOT EXISTS idx_ky_status ON ky_records(status);

CREATE TABLE IF NOT EXISTS workers (
    id          TEXT PRIMARY KEY,
    name        TEXT NOT NULL,
    kana        TEXT,
    company     TEXT NOT NULL,
    job         TEXT,
    birth       TEXT,
    blood       TEXT,
    insurance   TEXT,
    emergency   TEXT,
    cert_name   TEXT,
    cert_expiry TEXT,
    ccus        TEXT,
    qr_token    TEXT UNIQUE,
    created_at  TEXT DEFAULT (datetime('now','localtime'))
);
CREATE INDEX IF NOT EXISTS idx_workers_company ON workers(company);
CREATE INDEX IF NOT EXISTS idx_workers_qr      ON workers(qr_token);

CREATE TABLE IF NOT EXISTS safety_docs (
    id         TEXT PRIMARY KEY,
    doc_type   TEXT NOT NULL,
    company    TEXT NOT NULL,
    date       TEXT,
    note       TEXT,
    status     TEXT DEFAULT '提出済',
    created_at TEXT DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS attendance (
    id            TEXT PRIMARY KEY,
    worker_id     TEXT NOT NULL,
    date          TEXT NOT NULL,
    checkin_time  TEXT,
    checkout_time TEXT,
    method        TEXT DEFAULT 'manual',
    created_at    TEXT DEFAULT (datetime('now','localtime')),
    FOREIGN KEY (worker_id) REFERENCES workers(id) ON DELETE CASCADE
);
CREATE INDEX IF NOT EXISTS idx_att_date   ON attendance(date);
CREATE INDEX IF NOT EXISTS idx_att_worker ON attendance(worker_id);
"""

def init_db():
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        _migrate_columns(conn)
        _seed_companies(conn)

def _migrate_columns(conn):
    """既存DBに新カラムを追加（冪等）"""
    try:
        conn.execute("ALTER TABLE workers ADD COLUMN qr_token TEXT UNIQUE")
    except Exception:
        pass
    try:
        conn.execute("ALTER TABLE attendance ADD COLUMN method TEXT DEFAULT 'manual'")
    except Exception:
        pass
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_workers_qr ON workers(qr_token)")
    except Exception:
        pass

def _seed_companies(conn):
    defaults = [
        ('1', '\u5c71\u7530\u5efa\u8a2d\u682a\u5f0f\u4f1a\u793e', '\u9435\u7b4b'),
        ('2', '\u7530\u4e2d\u5de5\u696d\u682a\u5f0f\u4f1a\u793e', '\u578b\u679a'),
        ('3', '\u9234\u6728\u8a2d\u5099\u682a\u5f0f\u4f1a\u793e', '\u96fb\u6c17'),
        ('4', '\u4f50\u85e4\u571f\u6728\u682a\u5f0f\u4f1a\u793e', '\u571f\u5de5'),
    ]
    conn.executemany(
        "INSERT OR IGNORE INTO companies(id,name,type) VALUES (?,?,?)",
        defaults
    )

def rows_to_list(rows):
    return [dict(r) for r in rows]

# ------------------------------------------------------------------
# Companies
# ------------------------------------------------------------------
def get_companies():
    with get_conn() as conn:
        return rows_to_list(conn.execute("SELECT * FROM companies ORDER BY id").fetchall())

def add_company(id_, name, type_):
    with get_conn() as conn:
        conn.execute("INSERT OR IGNORE INTO companies(id,name,type) VALUES (?,?,?)", (id_, name, type_))

# ------------------------------------------------------------------
# Work Schedules
# ------------------------------------------------------------------
def get_schedules(filter_date=None):
    with get_conn() as conn:
        if filter_date:
            rows = conn.execute("SELECT * FROM work_schedules WHERE date=? ORDER BY time_start", (filter_date,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM work_schedules ORDER BY date DESC, time_start").fetchall()
        return rows_to_list(rows)

def add_schedule(s):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO work_schedules
                (id,date,company,work_content,location,workers_count,time_start,time_end,note,status)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (s['id'], s['date'], s['company'], s['work_content'],
              s.get('location'), s.get('workers_count', 1),
              s.get('time_start'), s.get('time_end'),
              s.get('note'), s.get('status', '予定')))

def update_schedule(sid, fields):
    allowed = {'work_content','location','workers_count','time_start','time_end','note','status'}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    clause = ', '.join(f"{k}=?" for k in updates)
    with get_conn() as conn:
        cur = conn.execute(f"UPDATE work_schedules SET {clause} WHERE id=?", list(updates.values()) + [sid])
        return cur.rowcount > 0

def delete_schedule(sid):
    with get_conn() as conn:
        conn.execute("DELETE FROM work_schedules WHERE id=?", (sid,))

# ------------------------------------------------------------------
# Equipment
# ------------------------------------------------------------------
def get_equipment(filter_date=None):
    with get_conn() as conn:
        if filter_date:
            rows = conn.execute("SELECT * FROM equipment_reservations WHERE date=? ORDER BY time_start", (filter_date,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM equipment_reservations ORDER BY date DESC, time_start").fetchall()
        return rows_to_list(rows)

def check_equipment_conflict(equipment, date_, time_start, time_end, exclude_id=None):
    with get_conn() as conn:
        q = "SELECT id FROM equipment_reservations WHERE equipment=? AND date=? AND time_start < ? AND time_end > ?"
        params = [equipment, date_, time_end, time_start]
        if exclude_id:
            q += " AND id != ?"; params.append(exclude_id)
        return conn.execute(q, params).fetchone() is not None

def add_equipment(r):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO equipment_reservations (id,date,equipment,company,time_start,time_end,purpose)
            VALUES (?,?,?,?,?,?,?)
        """, (r['id'], r['date'], r['equipment'], r['company'],
              r['time_start'], r['time_end'], r.get('purpose')))

def delete_equipment(eid):
    with get_conn() as conn:
        conn.execute("DELETE FROM equipment_reservations WHERE id=?", (eid,))

# ------------------------------------------------------------------
# KY Records
# ------------------------------------------------------------------
def get_ky_records(filter_date=None, status=None):
    with get_conn() as conn:
        q = "SELECT * FROM ky_records WHERE 1=1"; params = []
        if filter_date: q += " AND date=?"; params.append(filter_date)
        if status:      q += " AND status=?"; params.append(status)
        q += " ORDER BY created_at DESC"
        return rows_to_list(conn.execute(q, params).fetchall())

def add_ky(r):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO ky_records
                (id,date,company,work_content,danger_point,measure,check_method,level,signer,status)
            VALUES (?,?,?,?,?,?,?,?,?,?)
        """, (r['id'], r['date'], r['company'], r['work_content'],
              r.get('danger_point'), r.get('measure'), r.get('check_method'),
              r.get('level', 'medium'), r.get('signer'), '未承認'))

def approve_ky(kid):
    with get_conn() as conn:
        cur = conn.execute("""
            UPDATE ky_records SET status='承認済', approved_at=datetime('now','localtime') WHERE id=?
        """, (kid,))
        return cur.rowcount > 0

# ------------------------------------------------------------------
# Workers  (QR token support)
# ------------------------------------------------------------------
def get_workers(company=None):
    with get_conn() as conn:
        if company:
            rows = conn.execute("SELECT * FROM workers WHERE company=? ORDER BY kana, name", (company,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM workers ORDER BY company, kana, name").fetchall()
        return rows_to_list(rows)

def get_worker_by_id(wid):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM workers WHERE id=?", (wid,)).fetchone()
        return dict(row) if row else None

def get_worker_by_qr(token):
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM workers WHERE qr_token=?", (token,)).fetchone()
        return dict(row) if row else None

def add_worker(w):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO workers
                (id,name,kana,company,job,birth,blood,insurance,emergency,cert_name,cert_expiry,ccus,qr_token)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
        """, (w['id'], w['name'], w.get('kana'), w['company'],
              w.get('job'), w.get('birth'), w.get('blood'),
              w.get('insurance'), w.get('emergency'),
              w.get('cert_name'), w.get('cert_expiry'), w.get('ccus'),
              w.get('qr_token')))

def set_qr_token(worker_id, token):
    with get_conn() as conn:
        conn.execute("UPDATE workers SET qr_token=? WHERE id=?", (token, worker_id))

def delete_worker(wid):
    with get_conn() as conn:
        conn.execute("DELETE FROM workers WHERE id=?", (wid,))

def get_expiring_certs(days_threshold=30):
    today = date.today()
    limit = today + timedelta(days=days_threshold)
    with get_conn() as conn:
        rows = conn.execute("""
            SELECT name, cert_name, cert_expiry FROM workers
            WHERE cert_expiry IS NOT NULL AND cert_expiry != ''
              AND cert_expiry >= ? AND cert_expiry <= ?
            ORDER BY cert_expiry
        """, (today.isoformat(), limit.isoformat())).fetchall()
    result = []
    for r in rows:
        try:
            exp = date.fromisoformat(r['cert_expiry'])
            result.append({'name': r['name'], 'cert': r['cert_name'],
                           'expiry': r['cert_expiry'], 'days': (exp - today).days})
        except Exception:
            pass
    return result

# ------------------------------------------------------------------
# Safety Docs
# ------------------------------------------------------------------
def get_safety_docs():
    with get_conn() as conn:
        return rows_to_list(conn.execute("SELECT * FROM safety_docs ORDER BY created_at DESC").fetchall())

def add_safety_doc(d):
    with get_conn() as conn:
        conn.execute("""
            INSERT INTO safety_docs(id,doc_type,company,date,note,status) VALUES (?,?,?,?,?,?)
        """, (d['id'], d['doc_type'], d['company'], d.get('date'), d.get('note'), '提出済'))

# ------------------------------------------------------------------
# Attendance  (method: 'manual' | 'qr')
# ------------------------------------------------------------------
def get_attendance(filter_date=None):
    with get_conn() as conn:
        if filter_date:
            rows = conn.execute("""
                SELECT a.*, w.name AS worker_name, w.company, w.job, w.ccus, w.qr_token
                FROM attendance a LEFT JOIN workers w ON a.worker_id = w.id
                WHERE a.date=? ORDER BY a.checkin_time
            """, (filter_date,)).fetchall()
        else:
            rows = conn.execute("""
                SELECT a.*, w.name AS worker_name, w.company, w.job, w.ccus, w.qr_token
                FROM attendance a LEFT JOIN workers w ON a.worker_id = w.id
                ORDER BY a.date DESC, a.checkin_time
            """).fetchall()
        return rows_to_list(rows)

def checkin(worker_id, att_date, record_id, method='manual'):
    with get_conn() as conn:
        existing = conn.execute("""
            SELECT id FROM attendance WHERE worker_id=? AND date=? AND checkout_time IS NULL
        """, (worker_id, att_date)).fetchone()
        if existing:
            return False
        conn.execute("""
            INSERT INTO attendance(id,worker_id,date,checkin_time,method) VALUES (?,?,?,?,?)
        """, (record_id, worker_id, att_date, datetime.now().strftime('%H:%M'), method))
        return True

def checkout(worker_id, att_date, method='manual'):
    with get_conn() as conn:
        cur = conn.execute("""
            UPDATE attendance SET checkout_time=?, method=?
            WHERE worker_id=? AND date=? AND checkout_time IS NULL
        """, (datetime.now().strftime('%H:%M'), method, worker_id, att_date))
        return cur.rowcount > 0

def get_current_status(worker_id, att_date):
    with get_conn() as conn:
        row = conn.execute("""
            SELECT * FROM attendance WHERE worker_id=? AND date=? ORDER BY checkin_time DESC LIMIT 1
        """, (worker_id, att_date)).fetchone()
        return dict(row) if row else None

# ------------------------------------------------------------------
# Dashboard
# ------------------------------------------------------------------
def get_dashboard_stats(today_str):
    with get_conn() as conn:
        today_workers    = conn.execute("SELECT COUNT(*) FROM attendance WHERE date=?", (today_str,)).fetchone()[0]
        today_schedules  = conn.execute("SELECT COUNT(*) FROM work_schedules WHERE date=?", (today_str,)).fetchone()[0]
        pending_ky       = conn.execute("SELECT COUNT(*) FROM ky_records WHERE status='未承認'").fetchone()[0]
        recent_schedules = rows_to_list(conn.execute("""
            SELECT * FROM work_schedules WHERE date=? ORDER BY time_start LIMIT 5
        """, (today_str,)).fetchall())
        companies_count  = conn.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    expiring = get_expiring_certs(30)
    return {
        'today_workers': today_workers, 'today_schedules': today_schedules,
        'pending_ky': pending_ky, 'expiring_certs': len(expiring),
        'expiring_details': expiring, 'recent_schedules': recent_schedules,
        'companies_count': companies_count,
    }
