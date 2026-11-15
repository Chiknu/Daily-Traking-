"""SQLite storage layer for the multi-user Life Tracker.

Every query is scoped by user_id, so one user can never see another user's data.
"""
import hashlib
import hmac
import os
import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime, timedelta

DB_PATH = os.environ.get("TRACKER_DB", os.path.join("data", "tracker.db"))
PBKDF2_ITERATIONS = 200_000

SCHEMA = """
CREATE TABLE IF NOT EXISTS users(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL COLLATE NOCASE,
    salt BLOB NOT NULL,
    pw_hash BLOB NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS sessions(
    token_hash TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS habits(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    category TEXT,
    cue TEXT,
    active INTEGER DEFAULT 1
);
CREATE TABLE IF NOT EXISTS habit_logs(
    habit_id INTEGER NOT NULL REFERENCES habits(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    log_date TEXT NOT NULL,
    PRIMARY KEY(habit_id, log_date)
);
CREATE TABLE IF NOT EXISTS daily_notes(
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    log_date TEXT NOT NULL,
    note TEXT,
    PRIMARY KEY(user_id, log_date)
);
CREATE TABLE IF NOT EXISTS weekly_goals(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    week_start TEXT NOT NULL,
    goal TEXT NOT NULL,
    category TEXT,
    target_date TEXT,
    status TEXT,
    priority TEXT,
    impact TEXT,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS monthly_targets(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    month TEXT NOT NULL,
    focus_area TEXT NOT NULL,
    description TEXT,
    priority TEXT,
    progress TEXT,
    done INTEGER DEFAULT 0,
    notes TEXT
);
"""

# Whitelist of editable columns per table (first column is the required one).
COLS = {
    "habits": ["name", "category", "cue", "active"],
    "weekly_goals": ["goal", "week_start", "category", "target_date",
                     "status", "priority", "impact", "notes"],
    "monthly_targets": ["focus_area", "month", "description", "priority",
                        "progress", "done", "notes"],
}


@contextmanager
def conn():
    folder = os.path.dirname(DB_PATH)
    if folder:
        os.makedirs(folder, exist_ok=True)
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.execute("PRAGMA foreign_keys = ON")
    try:
        yield c
        c.commit()
    finally:
        c.close()


def init_db():
    with conn() as c:
        c.executescript(SCHEMA)


# ----------------------------------------------------------------- auth
def _hash(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)


def create_user(username: str, password: str):
    username = username.strip()
    salt = secrets.token_bytes(16)
    try:
        with conn() as c:
            c.execute(
                "INSERT INTO users(username, salt, pw_hash) VALUES(?,?,?)",
                (username, salt, _hash(password, salt)),
            )
        return True, "Account created! You can log in now."
    except sqlite3.IntegrityError:
        return False, "That username is already taken."


def authenticate(username: str, password: str):
    with conn() as c:
        row = c.execute(
            "SELECT id, username, salt, pw_hash FROM users WHERE username=?",
            (username.strip(),),
        ).fetchone()
    if row and hmac.compare_digest(_hash(password, row["salt"]), row["pw_hash"]):
        return {"id": row["id"], "username": row["username"]}
    return None


# -------------------------------------------------- persistent login (cookie)
SESSION_DAYS = 30


def _tok_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_session(user_id: int) -> str:
    """Create a login token (stored hashed). The raw token goes into a browser cookie."""
    token = secrets.token_urlsafe(32)
    exp = (datetime.utcnow() + timedelta(days=SESSION_DAYS)).isoformat()
    with conn() as c:
        c.execute("DELETE FROM sessions WHERE expires_at < ?", (datetime.utcnow().isoformat(),))
        c.execute("INSERT INTO sessions(token_hash, user_id, expires_at) VALUES(?,?,?)",
                  (_tok_hash(token), user_id, exp))
    return token


def user_from_token(token):
    if not token:
        return None
    with conn() as c:
        row = c.execute(
            "SELECT u.id, u.username FROM sessions s JOIN users u ON u.id = s.user_id "
            "WHERE s.token_hash=? AND s.expires_at > ?",
            (_tok_hash(token), datetime.utcnow().isoformat())).fetchone()
    return {"id": row["id"], "username": row["username"]} if row else None


def end_session(token):
    if token:
        with conn() as c:
            c.execute("DELETE FROM sessions WHERE token_hash=?", (_tok_hash(token),))


# ------------------------------------------------------- generic tables
def _clean(v):
    """Convert pandas/numpy values to plain sqlite-friendly python values."""
    if v is None:
        return None
    if hasattr(v, "item") and not isinstance(v, (str, bytes)):
        try:
            v = v.item()
        except (ValueError, AttributeError):
            pass
    if isinstance(v, float) and v != v:  # NaN
        return None
    if isinstance(v, bool):
        return int(v)
    if isinstance(v, (date, datetime)):
        return v.isoformat()[:10]
    if str(v) == "NaT":
        return None
    return v


def list_rows(table, user_id, scope_col=None, scope_val=None):
    cols = ["id"] + COLS[table]
    q = f"SELECT {', '.join(cols)} FROM {table} WHERE user_id=?"
    args = [user_id]
    if scope_col:
        assert scope_col in COLS[table]
        q += f" AND {scope_col}=?"
        args.append(scope_val)
    with conn() as c:
        return [dict(r) for r in c.execute(q + " ORDER BY id", args).fetchall()]


def save_rows(table, user_id, rows, scope_col=None, scope_val=None):
    """Sync `rows` (list of dicts, 'id' may be None for new) into the table.

    Rows are only added or updated - nothing is ever deleted from here, so users
    cannot remove their data. Rows with a blank required column are ignored.
    """
    cols = COLS[table]
    existing = {r["id"] for r in list_rows(table, user_id, scope_col, scope_val)}
    with conn() as c:
        for r in rows:
            r = {k: _clean(v) for k, v in r.items()}
            if scope_col:
                r[scope_col] = scope_val
            if not r.get(cols[0]) or not str(r[cols[0]]).strip():
                continue
            vals = [r.get(k) for k in cols]
            rid = r.get("id")
            if rid in existing:
                sets = ", ".join(f"{k}=?" for k in cols)
                c.execute(f"UPDATE {table} SET {sets} WHERE id=? AND user_id=?",
                          vals + [rid, user_id])
            else:
                names = ", ".join(["user_id"] + cols)
                marks = ", ".join("?" * (len(cols) + 1))
                c.execute(f"INSERT INTO {table}({names}) VALUES({marks})",
                          [user_id] + vals)


# ------------------------------------------------------- habit logging
def get_done(user_id, start: date, end: date):
    with conn() as c:
        rows = c.execute(
            "SELECT habit_id, log_date FROM habit_logs "
            "WHERE user_id=? AND log_date BETWEEN ? AND ?",
            (user_id, start.isoformat(), end.isoformat()),
        ).fetchall()
    return {(r["habit_id"], r["log_date"]) for r in rows}


def set_log(user_id, habit_id, day: date, done: bool):
    with conn() as c:
        owns = c.execute("SELECT 1 FROM habits WHERE id=? AND user_id=?",
                         (habit_id, user_id)).fetchone()
        if not owns:
            return
        if done:
            c.execute("INSERT OR IGNORE INTO habit_logs(habit_id, user_id, log_date) "
                      "VALUES(?,?,?)", (habit_id, user_id, day.isoformat()))
        else:
            c.execute("DELETE FROM habit_logs WHERE habit_id=? AND log_date=?",
                      (habit_id, day.isoformat()))


def get_notes(user_id, start: date, end: date):
    with conn() as c:
        rows = c.execute(
            "SELECT log_date, note FROM daily_notes "
            "WHERE user_id=? AND log_date BETWEEN ? AND ?",
            (user_id, start.isoformat(), end.isoformat()),
        ).fetchall()
    return {r["log_date"]: r["note"] for r in rows}


def set_note(user_id, day: date, note: str):
    with conn() as c:
        if note.strip():
            c.execute("INSERT INTO daily_notes(user_id, log_date, note) VALUES(?,?,?) "
                      "ON CONFLICT(user_id, log_date) DO UPDATE SET note=excluded.note",
                      (user_id, day.isoformat(), note.strip()))
        else:
            c.execute("DELETE FROM daily_notes WHERE user_id=? AND log_date=?",
                      (user_id, day.isoformat()))


def export_user(user_id):
    data = {t: list_rows(t, user_id) for t in COLS}
    with conn() as c:
        data["habit_logs"] = [dict(r) for r in c.execute(
            "SELECT habit_id, log_date FROM habit_logs WHERE user_id=?", (user_id,))]
        data["daily_notes"] = [dict(r) for r in c.execute(
            "SELECT log_date, note FROM daily_notes WHERE user_id=?", (user_id,))]
    return data
