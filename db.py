import sqlite3
import os
from typing import Optional

DB_PATH = os.getenv("DB_PATH", "bot.db")


# -----------------------------
# DB 基本工具
# -----------------------------
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# -----------------------------
# 初始化資料表
# -----------------------------
def init_db():
    conn = get_conn()
    cur = conn.cursor()

    # 使用者（用來推播提醒）
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_targets (
        user_id TEXT PRIMARY KEY,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 記帳資料
    cur.execute("""
    CREATE TABLE IF NOT EXISTS expenses (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id TEXT NOT NULL,
        amount REAL NOT NULL,
        category TEXT NOT NULL,
        memo TEXT,
        spent_date TEXT NOT NULL,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # 設定（提醒開關）
    cur.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    conn.commit()
    conn.close()


# -----------------------------
# 使用者（推播用）
# -----------------------------
def upsert_user_target(user_id: str):
    conn = get_conn()
    conn.execute("""
    INSERT OR IGNORE INTO user_targets (user_id)
    VALUES (?)
    """, (user_id,))
    conn.commit()
    conn.close()


def get_all_user_targets():
    conn = get_conn()
    rows = conn.execute("SELECT user_id FROM user_targets").fetchall()
    conn.close()
    return [r["user_id"] for r in rows]


# -----------------------------
# 記帳 CRUD
# -----------------------------
def add_expense(user_id: str, amount: float, category: str, memo: str, spent_date: str):
    conn = get_conn()
    conn.execute("""
    INSERT INTO expenses (user_id, amount, category, memo, spent_date)
    VALUES (?, ?, ?, ?, ?)
    """, (user_id, float(amount), category, memo, spent_date))
    conn.commit()
    conn.close()


def get_expenses_on(user_id: str, day: str):
    conn = get_conn()
    rows = conn.execute("""
    SELECT *
    FROM expenses
    WHERE user_id = ? AND spent_date = ?
    ORDER BY id ASC
    """, (user_id, day)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_expenses_between(user_id: str, d1: str, d2: str):
    conn = get_conn()
    rows = conn.execute("""
    SELECT *
    FROM expenses
    WHERE user_id = ?
      AND spent_date BETWEEN ? AND ?
    ORDER BY spent_date ASC, id ASC
    """, (user_id, d1, d2)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_expense_by_id(user_id: str, expense_id: int) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("""
    SELECT *
    FROM expenses
    WHERE user_id = ? AND id = ?
    """, (user_id, expense_id)).fetchone()
    conn.close()
    return dict(row) if row else None


def get_last_expense(user_id: str) -> Optional[dict]:
    conn = get_conn()
    row = conn.execute("""
    SELECT *
    FROM expenses
    WHERE user_id = ?
    ORDER BY spent_date DESC, id DESC
    LIMIT 1
    """, (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def delete_expense(user_id: str, expense_id: int) -> int:
    conn = get_conn()
    cur = conn.execute("""
    DELETE FROM expenses
    WHERE user_id = ? AND id = ?
    """, (user_id, expense_id))
    conn.commit()
    conn.close()
    return cur.rowcount  # 1 = 成功, 0 = 找不到


def update_expense(
    user_id: str,
    expense_id: int,
    amount=None,
    category=None,
    memo=None
) -> int:
    fields = []
    params = []

    if amount is not None:
        fields.append("amount = ?")
        params.append(float(amount))

    if category is not None:
        fields.append("category = ?")
        params.append(str(category))

    if memo is not None:
        fields.append("memo = ?")
        params.append(str(memo))

    if not fields:
        return 0

    params.extend([user_id, expense_id])

    conn = get_conn()
    cur = conn.execute(f"""
    UPDATE expenses
    SET {", ".join(fields)}
    WHERE user_id = ? AND id = ?
    """, params)
    conn.commit()
    conn.close()
    return cur.rowcount


# -----------------------------
# 設定（提醒）
# -----------------------------
def set_setting(key: str, value: str):
    conn = get_conn()
    conn.execute("""
    INSERT INTO settings (key, value)
    VALUES (?, ?)
    ON CONFLICT(key) DO UPDATE SET value = excluded.value
    """, (key, value))
    conn.commit()
    conn.close()


def get_setting(key: str, default: str = "0") -> str:
    conn = get_conn()
    row = conn.execute("""
    SELECT value FROM settings WHERE key = ?
    """, (key,)).fetchone()
    conn.close()
    return row["value"] if row else default
