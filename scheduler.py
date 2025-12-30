import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from linebot.models import TextSendMessage

from db import list_user_targets, get_setting, get_expenses_on
from utils import today_str

TZ = pytz.timezone("Asia/Taipei")
scheduler = BackgroundScheduler(timezone=TZ)

def job_no_expense_reminder(line_bot_api):
    if get_setting("no_expense_reminder_enabled", "1") != "1":
        return

    today = today_str()
    user_ids = list_user_targets()

    for uid in user_ids:
        rows = get_expenses_on(uid, today)
        if len(rows) == 0:
            try:
                line_bot_api.push_message(
                    uid,
                    TextSendMessage(text=f"🧾 今天（{today}）還沒記帳喔～\n回覆：記帳 金額 類別 [備註]")
                )
            except Exception:
                # 推播失敗就略過（可能封鎖/無權限/失效 userId）
                pass

def start_scheduler(line_bot_api):
    # 每天 21:00 提醒
    scheduler.add_job(
        job_no_expense_reminder,
        trigger=CronTrigger(hour=21, minute=0),
        args=[line_bot_api],
        id="no_expense_reminder_21",
        replace_existing=True
    )

    if not scheduler.running:
        scheduler.start()
