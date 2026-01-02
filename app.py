from flask import Flask, request, jsonify
import os
import requests

app = Flask(__name__)

NOTION_TOKEN = os.environ["NOTION_TOKEN"]
DATABASE_ID = os.environ["NOTION_DATABASE_ID"]
NOTION_VERSION = "2022-06-28"

HEADERS = {
    "Authorization": f"Bearer {NOTION_TOKEN}",
    "Content-Type": "application/json",
    "Notion-Version": NOTION_VERSION
}

@app.route("/")
def health():
    return "OK"

@app.post("/expense")
def add_expense():
    data = request.get_json(silent=True) or {}

    print("RAW JSON =", data)

    date = data.get("date")              # yyyy-MM-dd
    amount = int(data.get("amount", 0))
    category = data.get("category", "未分類")
    month = data.get("month", "十二月")
    note = data.get("note", "")

    title = f"[{category}] {amount}"

    payload = {
        "parent": {"database_id": DATABASE_ID},
        "properties": {
            "名稱": {
                "title": [
                    {"text": {"content": title}}
                ]
            },
            "日期": {
                "date": {"start": date}
            },
            "金額": {
                "number": amount
            },
            "類別": {
                "select": {"name": category}
            },
            "月份": {
                "select": {"name": month}
            },
            "備註": {
                "rich_text": [
                    {"text": {"content": note}}
                ]
            }
        }
    }

    r = requests.post(
        "https://api.notion.com/v1/pages",
        headers=HEADERS,
        json=payload
    )

    if r.status_code >= 400:
        print("NOTION ERROR:", r.text)
        return jsonify(ok=False, detail=r.text), r.status_code

    return jsonify(ok=True, detail=r.json())
