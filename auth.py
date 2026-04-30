# auth.py -- BuildeeMgr authentication layer
# Flask-Login + bcrypt password hashing
import sqlite3, bcrypt, uuid, secrets
from datetime import datetime, timedelta
from flask_login import UserMixin
import database as db

# ------------------------------------------------------------------
# User model (Flask-Login compatible)
# ------------------------------------------------------------------
class User(UserMixin):
    def __init__(self, row):
        self.id           = row['id']
        self.username     = row['username']
        self.display_name = row['display_name']
        self.role         = row['role']          # 'admin' | 'manager' | 'viewer'
        self.company      = row['company'] or ''
        self.is_active_   = bool(row['is_active'])

    def get_id(self):
        return self.id

    @property
    def is_active(self):
        return self.is_active_

    def is_admin(self):
        return self.role == 'admin'

    def can_write(self):
        return self.role in ('admin', 'manager')

    def to_dict(self):
        return {
            'id': self.id, 'username': self.username,
            'display_name': self.display_name,
            'role': self.role, 'company': self.company,
        }

ROLE_LABELS = {
    'admin':   ('管理者',   'red'),
    'manager': ('現場監督', 'orange'),
    'viewer':  ('閲覧者',  'blue'),
}

# ------------------------------------------------------------------
# DB helpers
# ------------------------------------------------------------------
def _conn():
    conn = sqlite3.connect(db.DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def init_auth_db():
    """Create users + sessions tables and seed a default admin."""
    with _conn() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id           TEXT PRIMARY KEY,
                username     TEXT NOT NULL UNIQUE,
                display_name TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                role         TEXT NOT NULL DEFAULT 'viewer',
                company      TEXT,
                is_active    INTEGER NOT NULL DEFAULT 1,
                last_login   TEXT,
                created_at   TEXT DEFAULT (datetime('now','localtime'))
            );
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);

            CREATE TABLE IF NOT EXISTS login_log (
                id         TEXT PRIMARY KEY,
                user_id    TEXT,
                username   TEXT,
                action     TEXT,
                ip         TEXT,
                success    INTEGER,
                created_at TEXT DEFAULT (datetime('now','localtime'))
            );
        """)
        # Default admin — only insert if no users exist
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        if count == 0:
            _create_user_internal(conn,
                username='admin',
                display_name='管理者',
                password='admin1234',
                role='admin',
                company='元請会社'
            )
            print("[Auth] Default admin created: admin / admin1234")

def _create_user_internal(conn, username, display_name, password, role, company=''):
    pw_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    uid = str(uuid.uuid4())
    conn.execute("""
        INSERT INTO users (id, username, display_name, password_hash, role, company)
        VALUES (?,?,?,?,?,?)
    """, (uid, username, display_name, pw_hash, role, company))
    return uid

# ------------------------------------------------------------------
# Public DAO
# ------------------------------------------------------------------
def get_user_by_id(uid):
    with _conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE id=?", (uid,)).fetchone()
        return User(row) if row else None

def get_user_by_username(username):
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=? AND is_active=1", (username,)
        ).fetchone()
        return User(row) if row else None

def get_all_users():
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM users ORDER BY role, username"
        ).fetchall()
        return [dict(r) for r in rows]

def verify_password(username, password):
    """Returns User on success, None on failure."""
    with _conn() as conn:
        row = conn.execute(
            "SELECT * FROM users WHERE username=? AND is_active=1", (username,)
        ).fetchone()
        if not row:
            return None
        if bcrypt.checkpw(password.encode(), row['password_hash'].encode()):
            conn.execute(
                "UPDATE users SET last_login=datetime('now','localtime') WHERE id=?",
                (row['id'],)
            )
            return User(row)
        return None

def create_user(username, display_name, password, role='viewer', company=''):
    """Returns (user_id, None) or (None, error_msg)."""
    with _conn() as conn:
        existing = conn.execute(
            "SELECT id FROM users WHERE username=?", (username,)
        ).fetchone()
        if existing:
            return None, f"ユーザー名 '{username}' は既に使われています"
        if len(password) < 8:
            return None, "パスワードは8文字以上にしてください"
        uid = _create_user_internal(conn, username, display_name, password, role, company)
        return uid, None

def update_user(uid, fields):
    """Update allowed fields. Returns True on success."""
    allowed = {'display_name', 'role', 'company', 'is_active'}
    updates = {k: v for k, v in fields.items() if k in allowed}
    if not updates:
        return False
    clause = ', '.join(f"{k}=?" for k in updates)
    with _conn() as conn:
        cur = conn.execute(
            f"UPDATE users SET {clause} WHERE id=?",
            list(updates.values()) + [uid]
        )
        return cur.rowcount > 0

def change_password(uid, new_password):
    if len(new_password) < 8:
        return False, "パスワードは8文字以上にしてください"
    pw_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
    with _conn() as conn:
        conn.execute("UPDATE users SET password_hash=? WHERE id=?", (pw_hash, uid))
    return True, None

def delete_user(uid):
    """Cannot delete the last admin."""
    with _conn() as conn:
        admin_count = conn.execute(
            "SELECT COUNT(*) FROM users WHERE role='admin' AND is_active=1"
        ).fetchone()[0]
        row = conn.execute("SELECT role FROM users WHERE id=?", (uid,)).fetchone()
        if row and row['role'] == 'admin' and admin_count <= 1:
            return False, "最後の管理者は削除できません"
        conn.execute("DELETE FROM users WHERE id=?", (uid,))
        return True, None

def log_login(user_id, username, action, ip, success):
    with _conn() as conn:
        conn.execute("""
            INSERT INTO login_log (id, user_id, username, action, ip, success)
            VALUES (?,?,?,?,?,?)
        """, (str(uuid.uuid4()), user_id, username, action, ip, 1 if success else 0))

def get_login_log(limit=50):
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM login_log ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
