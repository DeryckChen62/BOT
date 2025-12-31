import os
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_VERSION = os.getenv("NOTION_VERSION", "2022-06-28")

def headers():
    return {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json"
    }

@app.get("/")
def health():
    return {"ok": True}

@app.post("/expense")
def add_expense():
    data = request.json or {}

    title = f"【{data['category']}】{data['amount']}"

    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "名稱": {"title": [{"text": {"content": title}}]},
            "類別": {"select": {"name": data["category"]}},
            "日期": {"date": {"start": data["date"]}},
            "金額": {"number": float(data["amount"])},
            "月份": {"select": {"name": data["month"]}},
            "備註": {"rich_text": [{"text": {"content": data.get("note","")}}]}
        }
    }

    r = requests.post("https://api.notion.com/v1/pages", headers=headers(), json=payload)
    return jsonify({"ok": r.status_code < 300, "status": r.status_code, "detail": r.text})
