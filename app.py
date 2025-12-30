from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import json
import random
import re

from db import (
    init_db,
    upsert_user_target,
    add_expense,
    get_expenses_between,
    get_expenses_on,
    get_expense_by_id,
    get_last_expense,
    delete_expense,
    update_expense,
    set_setting,
    get_setting,
)
from utils import today_str, week_range_today, month_range_today, month_range_ym
from scheduler import start_scheduler

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
handler = WebhookHandler(os.getenv("LINE_CHANNEL_SECRET"))

# -----------------------------
# 關鍵字次數統計（JSON）
# -----------------------------
COUNT_FILE = "keyword_counts.json"

def load_counts():
    if os.path.exists(COUNT_FILE):
        with open(COUNT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_counts(data):
    with open(COUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

user_keyword_counts = load_counts()

# -----------------------------
# 鼓勵語錄
# -----------------------------
quotes = [
    "你已經比昨天更棒了耶 ✨",
    "不要小看現在努力的你，那是未來爆閃的伏筆！（•̀ᴗ•́）و",
    "你撐下來的每一秒，都是超帥氣的成就💪",
    "你很值得被愛，尤其是被自己愛 ❤️",
    "你能走到這裡已經超級了不起了 📍",
]

def get_positive_comment(score: int) -> str:
    if score >= 80:
        return "今天的你，光是站著就有氣場 ✨"
    elif score >= 50:
        return "穩穩前進中的好表現 👍"
    else:
        return "慢慢來沒關係，你已經在路上了 🌱"

# -----------------------------
# Help
# -----------------------------
HELP_TEXT = """📒 可用指令：

【記帳】
- 記帳 金額 類別 [備註]
- 查 YYYY-MM-DD（會顯示 #ID）
- 本週合計 / 本月合計
- 類別統計 [本週|本月|YYYY-MM]

【刪除 / 修改】
- 刪除 ID
- 刪除最後 / 刪除最後一筆
- 修改 ID 金額 X 類別 Y 備註 Z

【提醒】
- 提醒開 / 提醒關（每日 21:00）

【互動（群組）】
- 我今天好棒嗎
- 鼓勵我
"""

# -----------------------------
# Routes
# -----------------------------
@app.route("/")
def index():
    return "LINE Bot is running!"

@app.route("/callback", methods=["POST"])
def callback():
    signature = request.headers.get("X-Line-Signature", "")
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

# -----------------------------
# 記帳處理
# -----------------------------
def _handle_accounting(msg: str, user_id: str):
    if msg in ("help", "說明", "指令", "功能"):
        return HELP_TEXT

    # 記帳
    m = re.match(r"^記帳\s+(-?\d+(?:\.\d+)?)\s+(\S+)(?:\s+(.+))?$", msg)
    if m:
        amount = float(m.group(1))
        category = m.group(2)
        memo = (m.group(3) or "").strip()
        spent = today_str()
        add_expense(user_id, amount, category, memo, spent)
        return f"已記帳 ✅\n日期：{spent}\n金額：{amount}\n類別：{category}\n備註：{memo or '-'}"

    # 查某天（顯示 ID）
    m = re.match(r"^查\s+(\d{4}-\d{2}-\d{2})$", msg)
    if m:
        day = m.group(1)
        rows = get_expenses_on(user_id, day)
        if not rows:
            return f"{day} 沒有記帳紀錄。"
        total = 0
        lines = [f"{day} 記帳："]
        for r in rows:
            total += float(r["amount"])
            memo = (r.get("memo") or "-").strip() or "-"
            lines.append(f"# {r['id']}｜{r['amount']}｜{r['category']}｜{memo}")
        lines.append(f"合計：{total:.2f}")
        return "\n".join(lines)

    # 刪除指定
    m = re.match(r"^刪除\s+(\d+)$", msg)
    if m:
        eid = int(m.group(1))
        old = get_expense_by_id(user_id, eid)
        if not old:
            return f"找不到這筆記帳 ❌（#{eid}）"
        delete_expense(user_id, eid)
        memo = (old.get("memo") or "-").strip() or "-"
        return f"已刪除 ✅\n# {old['id']}｜{old['spent_date']}｜{old['amount']}｜{old['category']}｜{memo}"

    # 刪除最後一筆
    if msg in ("刪除最後", "刪除最後一筆"):
        old = get_last_expense(user_id)
        if not old:
            return "目前沒有任何記帳可刪除。"
        delete_expense(user_id, old["id"])
        memo = (old.get("memo") or "-").strip() or "-"
        return f"已刪除 ✅\n# {old['id']}｜{old['spent_date']}｜{old['amount']}｜{old['category']}｜{memo}"

    # 修改
    m = re.match(r"^修改\s+(\d+)\s+(.+)$", msg)
    if m:
        eid = int(m.group(1))
        rest = m.group(2).split()
        old = get_expense_by_id(user_id, eid)
        if not old:
            return f"找不到這筆記帳 ❌（#{eid}）"

        updates = {}
        i = 0
        while i < len(rest):
            key = rest[i]
            if key not in ("金額", "類別", "備註"):
                return "修改格式錯誤 ❌"
            updates[key] = rest[i + 1]
            i += 2

        update_expense(
            user_id,
            eid,
            amount=updates.get("金額"),
            category=updates.get("類別"),
            memo=updates.get("備註"),
        )

        new = get_expense_by_id(user_id, eid)
        return (
            "已更新 ✅\n"
            f"# {old['id']}｜{old['amount']}｜{old['category']} → "
            f"{new['amount']}｜{new['category']}"
        )

    return None

# -----------------------------
# Message Handler
# -----------------------------
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    msg = event.message.text.strip()
    user_id = event.source.user_id

    if user_id:
        upsert_user_target(user_id)
        reply = _handle_accounting(msg, user_id)
        if reply:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return

    # 群組互動（保留原功能）
    if event.source.type == "group":
        if msg in ("我今天好棒嗎", "今日好棒指數"):
            score = random.randint(1, 100)
            reply = f"🎯 今日好棒指數：{score}%\n{get_positive_comment(score)}"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return

        if msg == "鼓勵我":
            line_bot_api.reply_message(
                event.reply_token, TextSendMessage(text=random.choice(quotes))
            )
            return

# -----------------------------
# Init
# -----------------------------
init_db()
start_scheduler(line_bot_api)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)))

