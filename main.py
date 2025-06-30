from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import json
import random

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

COUNT_FILE = "keyword_counts.json"

def load_counts():
    if os.path.exists(COUNT_FILE):
        with open(COUNT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_counts(data):
    with open(COUNT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f)

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
    "今天也要記得笑一下，雖然笑不出來也沒關係，我幫你笑 (๑¯∀¯๑)"
]

def get_positive_comment(score):
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

@app.route("/")
def index():
    return "LINE Bot is running!"

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    global user_keyword_counts
    msg = event.message.text.strip().lower()
    user_id = event.source.user_id

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

        if msg in keyword_replies:
            if user_id not in user_keyword_counts:
                user_keyword_counts[user_id] = {}
            user_keyword_counts[user_id][msg] = user_keyword_counts[user_id].get(msg, 0) + 1
            save_counts(user_keyword_counts)

            count = user_keyword_counts[user_id][msg]
            reply = f"{keyword_replies[msg]}（你說過「{msg}」{count} 次）"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

        elif msg.startswith("查詢 "):
            keyword = msg.replace("查詢 ", "")
            count = user_keyword_counts.get(user_id, {}).get(keyword, 0)
            reply = f"你目前說「{keyword}」共 {count} 次。"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

        elif msg in ["我今天好棒嗎", "今日好棒指數"]:
            score = random.randint(1, 100)
            comment = get_positive_comment(score)
            reply = f"🎯 今日好棒指數為：{score}%\n{comment}"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))

        elif msg in ["金句", "來一句", "鼓勵我", "可愛語錄"]:
            quote = random.choice(quotes)
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=quote))

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
