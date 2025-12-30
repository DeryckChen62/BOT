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
    rows = conn.execute("SELECT user_id FROM user_ta

