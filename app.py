import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_VERSION = os.getenv("NOTION_VERSION", "2022-06-28")


def headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }


@app.get("/")
def health():
    return jsonify({"ok": True})


@app.post("/expense")
def add_expense():
    data = request.get_json(silent=True) or {}

    # ✅ 全部用 .get()，不會再 KeyError
    category = data.get("category", "未分類")
    amount_raw = data.get("amount", 0)
    date = data.get("date")              # 建議格式: "YYYY-MM-DD"
    month = data.get("month", "十二月")   # 先固定也 OK
    note = data.get("note", "")

    # ✅ amount 轉成 number（允許 "120" 這種字串）
    try:
        amount = float(amount_raw)
    except (TypeError, ValueError):
        amount = 0.0

    title = f"【{category}】{amount_raw}"

    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "名稱": {"title": [{"text": {"content": title}}]},
            "類別": {"select": {"name": category}},
            "日期": {"date": {"start": date}},
            "金額": {"number": amount},
            "月份": {"select": {"name": month}},
            "備註": {"rich_text": [{"text": {"content": note}}]},
        },
    }

    # ✅ 加 timeout，避免捷徑「要求逾時」
    r = requests.post(
        "https://api.notion.com/v1/pages",
        headers=headers(),
        json=payload,
        timeout=20,
    )

    return jsonify({"ok": r.status_code < 300, "status": r.status_code, "detail": r.text})
