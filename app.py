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
    set_setting,
    get_setting,
)
from utils import today_str, week_range_today, month_range_today, month_range_ym
from scheduler import start_scheduler

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# -----------------------------
# 原本的「關鍵字次數統計」(JSON)
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

quotes = [
    "你已經比昨天更棒了耶 ✨",
    "不要小看現在努力的你，那是未來爆閃的伏筆！（•̀ᴗ•́）و",
    "今天也是很讚的一天（因為有你在啊！）(๑´ㅂ`๑)",
    "你撐下來的每一秒，都是超帥氣的成就💪",
    "就算世界毀滅，你也記得吃飯睡覺喝水喔 ✧٩(ˊωˋ*)و✧",
    "你不是一顆螺絲，你是整個機器運轉的靈魂！٩(｡•́‿•̀｡)۶",
    "今天的你，光是站著就有氣場 ✨",
    "失敗了沒關係，我們下次可以一起怪天氣 ╮(╯∀╰)╭",
    "你是那種，即使偷偷 emo 還是會照亮別人的可愛存在 ✿",
    "今天也要記得笑一下，雖然笑不出來也沒關係，我幫你笑 (๑¯∀¯๑)",
    "全宇宙都沒你這麼努力的小廢柴（是讚的意思）🔥",
    "你已經很棒了，再偷懶一下也沒關係（認真）(｡•ᴗ-)✧",
    "別急著討厭自己，今天你已經很努力了 🐌",
    "你很值得被愛，尤其是被自己愛 ❤️",
    "今天累了就慢慢來，不趕時間 🐢",
    "偶爾當鹹魚也沒關係，鹹魚也很香啊（喂）",
    "你今天如果什麼都沒做，那也是努力活著的一種 ✊",
    "連 Google 都查不到你這種獨特 ✨",
    "天氣熱不熱不知道，但你一定是最暖的 ☀️",
    "再沒信心也拜託信一下自己，因為你值得 💖",
    "你做得比你自己以為的還要好很多很多喔 🍀",
    "你的人生進度沒有落後，只是版本不同 📅",
    "你今天也沒掉進人類觀察站（代表你很正常）🛸",
    "我不懂宇宙，但我懂你真的很努力 🌌",
    "別人看你是怎樣不重要，你要知道你是寶 ✨",
    "你不是在摸魚，是在水裡醞釀未來 🐠",
    "你能走到這裡已經超級了不起了 📍",
    "你有多溫柔我知道，因為訊息都很輕（？）💬",
    "當你懷疑自己時，我們都偷偷為你鼓掌中 👏",
    "你還在撐，這件事本身就值得慶祝 🎉"
]

def get_positive_comment(score: int) -> str:
    if score >= 96:
        return random.choice([
            "這不是好棒，是傳奇了 ✨",
            "你今天可以寫進教科書的那種棒 👑",
            "氣場強到貓都會自動過來蹭你 🐱",
            "棒到讓我開始懷疑人生是不是你安排的 🤯",
            "請問你是不是有練隱藏技能？怎麼這麼亮！🌈"
        ])
    elif score >= 80:
        return random.choice([
            "今天的你，光是站著就有氣場 ✨",
            "閃閃發亮欸～要不要戴墨鏡面對你 🕶️",
            "這麼棒，出去一定有貓自動跟你回家 🐾",
            "棒到我都想幫你做一支廣告了 📣",
            "是穩定輸出的優質人類，給你五顆星 🌟"
        ])
    elif score >= 60:
        return random.choice([
            "今天的你，是那種會被偷偷讚賞的類型 🫶",
            "表現不錯耶～這種棒，是細水長流型 🏞️",
            "今天有點像抹茶蛋糕，不甜膩但很耐吃 🍵",
            "穩穩地前進，腳步不大但不會停 ✨",
            "是讓人想輕聲說『你好棒』的那種棒"
        ])
    elif score >= 40:
        return random.choice([
            "可能沒開全力，但還是有默默發光 ✨",
            "像個小暖陽，沒有刺眼，但溫暖存在 ☀️",
            "今天可能是在蓄能，為明天大爆發做準備 🔋",
            "有種靜靜的棒，不需要誰知道也不怕孤單 🌿",
            "一步一步來，你的節奏剛剛好 🐢"
        ])
    elif score >= 20:
        return random.choice([
            "今天是成長中版本的你，最值得鼓掌 👏",
            "沒關係～你現在只是蓄氣中的賽亞人！⚡️",
            "有時候輕輕走，也是一種力量 🕊️",
            "你今天選擇慢下來，也是一種智慧 🍃",
            "再撐一下，棒棒力正在充電中 🔋"
        ])
    else:
        return random.choice([
            "今天的你像被雲蓋住的太陽，但光還在 ☁️☀️",
            "氣氛低一點沒關係，靜靜的你也很棒 🌌",
            "你只是剛好遇到需要充電的一天，不用急 🧃",
            "今天的你很柔軟，柔軟也很美 🍡",
            "有時候發呆，也是一種自我照顧 🛋️"
        ])

HELP_TEXT = """可用指令：
【記帳】
- 記帳 金額 類別 [備註...]
- 本週合計
- 本月合計
- 查 YYYY-MM-DD
- 類別統計 [本週|本月|YYYY-MM]
- 提醒開 / 提醒關（每天 21:00 檢查今日是否記帳）

【互動（群組可用）】
- 我今天好棒嗎 / 今日好棒指數
- 鼓勵我
- 查詢 關鍵字（查你在群組說某關鍵字的次數）
"""

@app.route("/")
def index():
    return "LINE Bot is running!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

def _handle_accounting(msg_raw: str, user_id: str):
    """
    Return reply text if matched; otherwise None
    """
    if msg_raw in ("help", "說明", "指令", "功能"):
        return HELP_TEXT

    # 記帳 金額 類別 [備註...]
    m = re.match(r"^記帳\s+(-?\d+(?:\.\d+)?)\s+(\S+)(?:\s+(.+))?$", msg_raw)
    if m:
        amount = float(m.group(1))
        category = m.group(2).strip()
        memo = (m.group(3) or "").strip()
        spent = today_str()
        add_expense(user_id=user_id, amount=amount, category=category, memo=memo, spent_date=spent)
        return f"已記帳 ✅\n日期：{spent}\n金額：{amount}\n類別：{category}\n備註：{memo or '-'}"

    if msg_raw == "本週合計":
        d1, d2 = week_range_today()
        rows = get_expenses_between(user_id, d1, d2)
        total = sum(float(r["amount"]) for r in rows)
        return f"本週（{d1}～{d2}）合計：{total:.2f}\n筆數：{len(rows)}"

    if msg_raw == "本月合計":
        d1, d2 = month_range_today()
        rows = get_expenses_between(user_id, d1, d2)
        total = sum(float(r["amount"]) for r in rows)
        return f"本月（{d1}～{d2}）合計：{total:.2f}\n筆數：{len(rows)}"

    m = re.match(r"^查\s+(\d{4}-\d{2}-\d{2})$", msg_raw)
    if m:
        day = m.group(1)
        rows = get_expenses_on(user_id, day)
        if not rows:
            return f"{day} 沒有記帳紀錄。"
        lines = [f"{day} 記帳："]
        total = 0.0
        for r in rows[:50]:
            total += float(r["amount"])
            memo = (r.get("memo") or "").strip()
            lines.append(f'- {r["amount"]}｜{r["category"]}｜{memo}')
        lines.append(f"合計：{total:.2f}（{len(rows)} 筆）")
        return "\n".join(lines)

    m = re.match(r"^類別統計(?:\s+(本週|本月|\d{4}-\d{2}))?$", msg_raw)
    if m:
        mode = m.group(1) or "本月"
        if mode == "本週":
            d1, d2 = week_range_today()
            label = f"本週（{d1}～{d2}）"
        elif mode == "本月":
            d1, d2 = month_range_today()
            label = f"本月（{d1}～{d2}）"
        else:
            d1, d2 = month_range_ym(mode)
            label = f"{mode}（{d1}～{d2}）"

        rows = get_expenses_between(user_id, d1, d2)
        if not rows:
            return f"{label} 沒有記帳紀錄。"
        by_cat = {}
        for r in rows:
            cat = r["category"]
            by_cat[cat] = by_cat.get(cat, 0.0) + float(r["amount"])
        items = sorted(by_cat.items(), key=lambda x: x[1], reverse=True)
        lines = [f"{label} 類別統計："]
        for cat, amt in items[:20]:
            lines.append(f"- {cat}: {amt:.2f}")
        lines.append(f"合計：{sum(by_cat.values()):.2f}")
        return "\n".join(lines)

    if msg_raw == "提醒開":
        set_setting("no_expense_reminder_enabled", "1")
        return "記帳提醒已開啟 ✅（每日 21:00 檢查）"

    if msg_raw == "提醒關":
        set_setting("no_expense_reminder_enabled", "0")
        return "記帳提醒已關閉 ✅"

    return None

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global user_keyword_counts

    msg_raw = event.message.text.strip()
    msg = msg_raw.lower()
    user_id = event.source.user_id  # may exist in group/room/user (depends on LINE settings)

    # 記錄 user 以便推播提醒
    if user_id:
        upsert_user_target(user_id)

    # 先處理記帳功能（群組/私訊都可用；但需要 user_id）
    if user_id:
        acc_reply = _handle_accounting(msg_raw, user_id)
        if acc_reply:
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=acc_reply))
            return
    else:
        # 沒拿到 user_id 時，仍可回 help
        if msg_raw in ("help", "說明", "指令", "功能"):
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=HELP_TEXT))
            return

    # 下面是你原本的互動功能：維持「群組」才有
    if event.source.type == 'group':
        keyword_replies = {
            "不好": "你很好!!你很好!!你很好!!",
            "睏了": "去睡啦不要撐",
            "吃飽沒": "還沒你請嗎？",
            "不要": "偏要 (*´∀`)~♥",
            "還好": "真的還好嗎？還是說你嘴硬（๑•́‧̫•̀๑）",
            "普通": "平凡也是一種幸福啦（๑•̀ㅁ•́๑）✧",
            "我不好": "哪裡不好？我看你很讚啊 💪",
            "好累": "快去休息！我在這裡等你回來٩(๑•̀ω•́๑)۶",
            "廢物": "你不是廢物，是超級廢物戰士（誤）其實你很棒啦（ﾉ>ω<）ﾉ"
        }

        if msg_raw in keyword_replies:
            if user_id not in user_keyword_counts:
                user_keyword_counts[user_id] = {}
            user_keyword_counts[user_id][msg_raw] = user_keyword_counts[user_id].get(msg_raw, 0) + 1
            save_counts(user_keyword_counts)

            count = user_keyword_counts[user_id][msg_raw]
            reply = f"{keyword_replies[msg_raw]}（你說過「{msg_raw}」{count} 次）"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return

        if msg.startswith("查詢 "):
            keyword = msg_raw.replace("查詢 ", "", 1).strip()
            count = user_keyword_counts.get(user_id, {}).get(keyword, 0)
            reply = f"你目前說「{keyword}」共 {count} 次。"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return

        if msg_raw in ["我今天好棒嗎", "今日好棒指數"]:
            score = random.randint(1, 100)
            comment = get_positive_comment(score)
            reply = f"🎯 今日好棒指數為：{score}%\n{comment}"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
            return

        if msg_raw in ["鼓勵我"]:
            quote = random.choice(quotes)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=quote))
            return

# -----------------------------
# 初始化 DB & 排程（提醒功能）
# -----------------------------
init_db()
start_scheduler(line_bot_api)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
