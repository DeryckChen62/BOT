# BOT（整合記帳功能版，無公告）

此專案基於你現有的 Flask + line-bot-sdk v2 Bot，新增「記帳＋統計＋提醒」功能，並保留原本群組互動功能。

## 功能
### 記帳（群組/私訊皆可用）
- 記帳：`記帳 金額 類別 [備註...]`
- 本週合計：`本週合計`
- 本月合計：`本月合計`
- 查某天：`查 YYYY-MM-DD`
- 類別統計：`類別統計 [本週|本月|YYYY-MM]`
- 記帳提醒：每天 21:00 檢查今日是否記帳（推播）
  - `提醒開` / `提醒關`

> 提醒推播需要 bot 有記錄到你的 userId（你只要跟 bot 互動過一次就會記錄）。

### 群組互動（保留）
- 關鍵字回覆＋次數統計（存 `keyword_counts.json`）
- `查詢 關鍵字`
- `我今天好棒嗎` / `今日好棒指數`
- `鼓勵我`

## 快速開始
```bash
pip install -r requirements.txt
cp .env.example .env
# 填入 LINE token/secret
python app.py
```

Webhook：`/callback`
健康檢查：`/`
