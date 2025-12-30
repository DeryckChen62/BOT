import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).resolve().parent / "bot.db"

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_targets (
        user_id TEXT PRIMARY KEY,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        memo TEXT,
        spent_date TEXT NOT NULL,   -- YYYY-MM-DD
        created_at TEXT NOT NULL
    )
    """)

    now = datetime.utcnow().isoformat()
    cur.execute("INSERT OR IGNORE INTO settings(key,value,updated_at) VALUES(?,?,?)",
                ("no_expense_reminder_enabled", "1", now))

    conn.commit()
    conn.close()

def upsert_user_target(user_id: str):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute("""
    INSERT INTO user_targets(user_id, created_at, updated_at)
    VALUES(?,?,?)
    ON CONFLICT(user_id) DO UPDATE SET updated_at=excluded.updated_at
    """, (user_id, now, now))
    conn.commit()
    conn.close()

def list_user_targets():
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM user_targets").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]

def set_setting(key: str, value: str):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute("""
    INSERT INTO settings(key,value,updated_at) VALUES(?,?,?)
    ON CONFLICT(key) DO UPDATE SET value=excluded.value, updated_at=excluded.updated_at
    """, (key, value, now))
    conn.commit()
    conn.close()

def get_setting(key: str, default: str = "") -> str:
    conn = get_conn()
    row = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return row["value"] if row else default

def add_expense(user_id: str, amount: float, category: str, memo: str, spent_date: str):
    now = datetime.utcnow().isoformat()
    conn = get_conn()
    conn.execute("""
    INSERT INTO expenses(user_id, amount, category, memo, spent_date, created_at)
    VALUES(?,?,?,?,?,?)
    """, (user_id, amount, category, memo, spent_date, now))
    conn.commit()
    conn.close()

def get_expenses_between(user_id: str, date_from: str, date_to: str):
    conn = get_conn()
    rows = conn.execute("""
    SELECT * FROM expenses
    WHERE user_id=? AND spent_date BETWEEN ? AND ?
    ORDER BY spent_date DESC, id DESC
    """, (user_id, date_from, date_to)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_expenses_on(user_id: str, day: str):
    conn = get_conn()
    rows = conn.execute("""
    SELECT * FROM expenses
    WHERE user_id=? AND spent_date=?
    ORDER BY id DESC
    """, (user_id, day)).fetchall()
    conn.close()
    return [dict(r) for r in rows]
