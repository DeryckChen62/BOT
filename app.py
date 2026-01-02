import os
import json
from datetime import datetime, timezone
from flask import Flask, request, jsonify
import requests

app = Flask(__name__)

# -----------------------------
# ENV
# -----------------------------
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "").strip()
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "").strip()
NOTION_VERSION = os.getenv("NOTION_VERSION", "2022-06-28").strip()

# 你的 Notion 資料庫欄位名稱（照你目前的表格：名稱/類別/日期/金額/月份/備註）
PROP_TITLE = os.getenv("NOTION_PROP_TITLE", "名稱")
PROP_CATEGORY = os.getenv("NOTION_PROP_CATEGORY", "類別")
PROP_DATE = os.getenv("NOTION_PROP_DATE", "日期")
PROP_AMOUNT = os.getenv("NOTION_PROP_AMOUNT", "金額")
PROP_MONTH = os.getenv("NOTION_PROP_MONTH", "月份")
PROP_NOTE = os.getenv("NOTION_PROP_NOTE", "備註")

NOTION_API_BASE = "https://api.notion.com/v1"


# -----------------------------
# Helpers
# -----------------------------
def now_iso():
    return datetime.now(timezone.utc).isoformat()


def _unwrap_shortcuts_payload(data: dict) -> dict:
    """
    iOS Shortcuts 有時會把真正的 payload 包在 '' 這個 key 裡，導致 data.get('amount') 變 None
    這裡做容錯解包。
    """
    if not isinstance(data, dict):
        return {}
    if "amount" not in data and "" in data and isinstance(data[""], dict):
        return data[""]
    return data


def _coerce_amount(value):
    """
    讓 amount 最終變成 number (int/float)，Notion number 才會吃。
    支援：777、"777"、"777.5"、"1,234"、"$777" 這類。
    """
    if value is None:
        return 0

    if isinstance(value, (int, float)):
        return value

    if isinstance(value, str):
        s = value.strip()
        # 移除常見符號/千分位
        for ch in [",", "$", "NT$", "NTD", "TWD", "元", " "]:
            s = s.replace(ch, "")
        if s == "":
            return 0
        try:
            if "." in s:
                return float(s)
            return int(s)
        except ValueError:
            return 0

    # 其他型別一律 fallback
    return 0


def _coerce_date(value):
    """
    Notion date.start 需要字串，建議 "YYYY-MM-DD"
    支援：
      - "2026-01-02"
      - datetime-ish（iOS 可能給 ISO）
    """
    if value is None:
        return None

    if isinstance(value, str):
        s = value.strip()
        if not s:
            return None
        # 若已經是 YYYY-MM-DD 就直接回
        if len(s) == 10 and s[4] == "-" and s[7] == "-":
            return s
        # 嘗試 parse ISO
        try:
            # Python 3.11+ 支援 fromisoformat，但有 Z 時先換掉
            s2 = s.replace("Z", "+00:00")
            dt = datetime.fromisoformat(s2)
            return dt.date().isoformat()
        except Exception:
            # 最後 fallback：直接回原字串（如果你確定捷徑給的是 YYYY-MM-DD 以外格式，建議改捷徑）
            return s

    # 其他型別：不要硬塞，避免 Notion 驗證失敗
    return None


def _build_title(category: str, amount) -> str:
    cat = category or "未分類"
    return f"[{cat}] {amount}"


def notion_create_page(payload):
    if not NOTION_TOKEN or not NOTION_DATABASE_ID:
        return False, 500, {"error": "Missing NOTION_TOKEN or NOTION_DATABASE_ID in environment variables."}

    url = f"{NOTION_API_BASE}/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_TOKEN}",
        "Content-Type": "application/json",
        "Notion-Version": NOTION_VERSION,
    }

    resp = requests.post(url, headers=headers, data=json.dumps(payload), timeout=20)
    try:
        data = resp.json()
    except Exception:
        data = {"raw": resp.text}

    ok = 200 <= resp.status_code < 300
    return ok, resp.status_code, data


# -----------------------------
# Routes
# -----------------------------
@app.get("/")
def health():
    return jsonify(
        ok=True,
        service="notion-expense-webhook",
        time=now_iso(),
        routes=["GET /", "GET /expense", "POST /expense"],
    )


@app.get("/expense")
def expense_get():
    # 讓你用瀏覽器打網址也不會跳 Method Not Allowed
    return jsonify(ok=True, hint="Use POST /expense with JSON body: {date, amount, category, month, note}"), 200


@app.post("/expense")
def add_expense():
    raw = request.get_json(silent=True) or {}
    data = _unwrap_shortcuts_payload(raw)

    # Debug：看捷徑到底送了什麼（Render Logs 會看到）
    print("RAW JSON =", raw)
    print("UNWRAPPED JSON =", data)
    print("RAW amount =", data.get("amount"), type(data.get("amount")))

    # 讀欄位（給預設值避免 KeyError）
    category = data.get("category") or "未分類"
    month = data.get("month") or "十二月"
    note = data.get("note") or ""

    amount = _coerce_amount(data.get("amount"))
    date_str = _coerce_date(data.get("date"))

    # date_str 不能是 None，否則 Notion 會報：date.start should be a string, instead was null
    if not date_str:
        return jsonify(
            ok=False,
            status=400,
            error="Missing/invalid date. Please send 'date' as a string like 'YYYY-MM-DD'.",
            received=data,
        ), 400

    title = _build_title(str(category), amount)

    # Notion payload：對應你資料庫的欄位型態
    notion_payload = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            PROP_TITLE: {"title": [{"type": "text", "text": {"content": title}}]},
            PROP_CATEGORY: {"select": {"name": str(category)}},
            PROP_DATE: {"date": {"start": date_str}},
            PROP_AMOUNT: {"number": amount},
            PROP_MONTH: {"select": {"name": str(month)}},
            PROP_NOTE: {"rich_text": [{"type": "text", "text": {"content": str(note)}}]} if str(note).strip() else {"rich_text": []},
        },
    }

    ok, status, notion_resp = notion_create_page(notion_payload)

    if not ok:
        return jsonify(ok=False, status=status, detail=notion_resp, sent=notion_payload), status

    return jsonify(ok=True, status=status, detail=notion_resp), 200


# -----------------------------
# Entrypoint
# -----------------------------
if __name__ == "__main__":
    port = int(os.getenv("PORT", "10000"))
    app.run(host="0.0.0.0", port=port)
