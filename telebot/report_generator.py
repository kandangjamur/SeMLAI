import pandas as pd
from telegram import Bot, ParseMode
from dotenv import load_dotenv
import os
from utils.logger import log

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TOKEN)

def generate_daily_summary():
    try:
        df = pd.read_csv("logs/signals_log.csv")
        today = pd.Timestamp.now().normalize()

        today_signals = df[pd.to_datetime(df["timestamp"], unit='s').dt.normalize() == today]

        total = len(today_signals)
        tp1 = len(today_signals[today_signals["status"] == "HIT TP1"])
        tp2 = len(today_signals[today_signals["status"] == "HIT TP2"])
        tp3 = len(today_signals[today_signals["status"] == "HIT TP3"])
        sl = len(today_signals[today_signals["status"] == "SL HIT"])

        msg = (
            f"📊 *Daily Signal Report*\n\n"
            f"📅 Date: `{today.date()}`\n"
            f"📈 Total Signals: *{total}*\n"
            f"✅ TP1 Hit: *{tp1}*\n"
            f"✅ TP2 Hit: *{tp2}*\n"
            f"🏆 TP3 Hit: *{tp3}*\n"
            f"❌ SL Hit: *{sl}*\n"
        )
        bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
        log("📤 Daily report sent to Telegram.")

    except Exception as e:
        log(f"❌ Daily Report Error: {e}")
