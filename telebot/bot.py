import os
import csv
from datetime import datetime
from telegram import Bot, ParseMode
from dotenv import load_dotenv

load_dotenv()

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
chat_id = os.getenv("TELEGRAM_CHAT_ID")

def generate_daily_summary():
    try:
        log_file = "logs/signals_log.csv"
        if not os.path.exists(log_file):
            return

        with open(log_file, "r") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        today = datetime.now().strftime("%Y-%m-%d")
        today_rows = [r for r in rows if r["datetime"].startswith(today)]

        if not today_rows:
            return

        total = len(today_rows)
        tp1 = len([r for r in today_rows if r["status"] == "TP1"])
        tp2 = len([r for r in today_rows if r["status"] == "TP2"])
        tp3 = len([r for r in today_rows if r["status"] == "TP3"])
        sl = len([r for r in today_rows if r["status"] == "SL"])
        spot = len([r for r in today_rows if r["type"] == "Spot"])
        scalp = len([r for r in today_rows if r["type"] == "Scalping"])
        normal = len([r for r in today_rows if r["type"] == "Normal"])

        success = tp1 + tp2 + tp3
        fail = sl

        msg = (
            f"📊 *Daily Report ({today})*\n\n"
            f"Total Signals: *{total}*\n"
            f"🟢 TP1: {tp1} | TP2: {tp2} | TP3: {tp3}\n"
            f"🔴 SL: {sl}\n\n"
            f"Types:\n"
            f"• Spot: {spot}\n"
            f"• Scalping: {scalp}\n"
            f"• Normal: {normal}\n\n"
            f"✅ Success: *{success}*\n"
            f"❌ Failed: *{fail}*"
        )

        bot.send_message(chat_id=chat_id, text=msg, parse_mode=ParseMode.MARKDOWN)

    except Exception as e:
        print(f"[Report Error] {e}")
