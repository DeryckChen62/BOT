
from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os
import json

app = Flask(__name__)

line_bot_api = LineBotApi(os.getenv('LINE_CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('LINE_CHANNEL_SECRET'))

# 儲存用戶關鍵字次數的 JSON 檔案
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

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 5000)))
