from datetime import datetime, timedelta
import pytz

TZ = pytz.timezone("Asia/Taipei")

def today_str():
    return datetime.now(TZ).strftime("%Y-%m-%d")

def week_range_today():
    now = datetime.now(TZ)
    start = now - timedelta(days=now.weekday())  # Monday
    end = start + timedelta(days=6)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def month_range_today():
    now = datetime.now(TZ)
    start = now.replace(day=1)
    if start.month == 12:
        next_month = start.replace(year=start.year + 1, month=1, day=1)
    else:
        next_month = start.replace(month=start.month + 1, day=1)
    end = next_month - timedelta(days=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

def month_range_ym(ym: str):
    year, month = map(int, ym.split("-"))
    start = TZ.localize(datetime(year, month, 1))
    if month == 12:
        next_month = TZ.localize(datetime(year + 1, 1, 1))
    else:
        next_month = TZ.localize(datetime(year, month + 1, 1))
    end = next_month - timedelta(days=1)
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")
