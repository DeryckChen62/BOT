import os
import json
from datetime import datetime, timezone, timedelta

import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID")
NOTION_VERSION = os.getenv("NOTION_VERSION", "2022-06-28")

TZ_TAIPEI = timezone(timedelta(hours=8))

def unwrap_payload(data):
    """
    Shortcuts 有時候會把 JSON 包一層，變成 {"": {...}} 或 {"data": {...}}。
    這裡把它剝回真正的 dict。
    """
    if not isinstance(data, dict):
        return {}

    # 連剝兩層，避免很怪的巢狀
    for _ in range(2):
        if len(data) == 1:
            k = next(iter(data.keys()))
            v = data.get(k)
            if isinstance(v, dict) and k in ("", "data", "payload", "body"):
                data = v
                continue
        break

    return data if isinstance(data, dict) else {}

def to_text(x, default=""):
    if x is None:
        return default
    if isinstance(x, str):
        return x
    if isinstance(x, (int, float, bool)):
        return str(x)
    if isinstance(x, dict):
        # 可能會有 {"name": "..."} 或 {"value": "..."}
        for key in ("name", "value", "text", "title"):
            if key in x and isinstance(x[key], str):
                return x[key]
        return default
    if isinstance(x, list):
        # 取第一個可轉文字的
        for item in x:
            s = to_text(item, "")
            if s:
                return s
        return default
    return default

def to_number(x, default=0):
    if x is None:
        return default
    if isinstance(x, (int, float)):
        return x
    if isinstance(x, str):
        try:
            # "100" / "100.5"
            n = float(x.strip())
            # 如果是整數就回 int（Notion number 其實都可）
            return int(n) if n.is_integer() else n
        except Exception:
            return default
    if isinstance(x, dict) and "value" in x:
        return to_number(x.get("value"), default)
    return default

def normalize_date(date_value):
    """
    Notion date.start 必須是字串：
    - "YYYY-MM-DD"
    - 或 ISO 8601 datetime
    """
    # Shortcuts 可能丟 dict: {"start": "..."} 之類
    if isinstance(date_value, dict):
        date_value = date_value.get("start")

    s = to_text(date_value, "").strip()

    if not s:
        # 沒傳就用今天（台北）
        return datetime.now(TZ_TAIPEI).date().isoformat()

    # 如果已經是 "YYYY-MM-DD" 就直接用
    if len(s) == 10 and s[4] == "-" and s[7] == "-":
        return s

    # 嘗試解析其他格式（保底）
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.date().isoformat()
    except Exception:
        # 解析不了就用今天，避免 Notion 報 null
        return datetime.now(TZ_TAIPEI).date().isoformat()

def month_from_date(date_str):
    # date_str: YYYY-MM-DD
    try:
        m = int(date_str.split("-")[1])
    except Exception:
        return "十二月"
    mapping = ["一月","二月","三月","四月","五月","六月","七月","八月","九月","十月","十一月","十二月"]
    return mapping[m-1] if 1 <= m <= 12 else "十二月"

@app.get("/")
def home():
    return "ok", 200

@app.get("/health")
def health():
    return jsonify(ok=True), 200

@app.post("/expense")
def add_expense():
    raw = request.get_json(silent=True)

    # 有時候 Shortcuts 會送成純文字 JSON
    if raw is None:
        try:
            raw = json.loads(request.data.decode("utf-8"))
        except Exception:
            raw = {}

    print("RAW JSON =", raw)

    data = unwrap_payload(raw)
    print("UNWRAPPED JSON =", data)

    # 取值（全部容錯）
    category = to_text(data.get("category"), "未分類").strip() or "未分類"
    amount = to_number(data.get("amount"), 0)
    date_str = normalize_date(data.get("date"))
    month = to_text(data.get("month"), "").strip()
    note = to_text(data.get("note"), "").strip()

    # 如果 month 被你不小心塞成 "2026-01-02" 這種，就改用 date 算月份
    if not month or (len(month) == 10 and month[4] == "-" and month[7] == "-"):
        month = month_from_date(date_str)

    title = f"[{category}] {amount}"

    # Notion Create Page
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }
    payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "名稱": {"title": [{"text": {"content": title}}]},
            "類別": {"select": {"name": category}},
            "日期": {"date": {"start": date_str}},
            "金額": {"number": amount},
            "月份": {"select": {"name": month}},
            "備註": {"rich_text": [{"text": {"content": note}}]},
        },
    }

    r = requests.post(url, headers=headers, json=payload, timeout=20)
    try:
        resp_json = r.json()
    except Exception:
        resp_json = {"raw": r.text}

    if r.status_code >= 400:
        print("NOTION ERROR =", resp_json)
        return jsonify(ok=False, status=r.status_code, detail=resp_json), 400

    return jsonify(ok=True, status=r.status_code, detail=resp_json), 200


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    app.run(host="0.0.0.0", port=port)

