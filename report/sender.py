import os
import pandas as pd
from datetime import datetime
from telegram import Bot
from dotenv import load_dotenv
from utils.logger import log

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = Bot(token=TOKEN)

def send_daily_report():
    try:
        path = "logs/signals_log.csv"
        if not os.path.exists(path):
            log("📭 No log file found for report.")
            return

        df = pd.read_csv(path)
        today = datetime.now().strftime("%Y-%m-%d")
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df_today = df[df['timestamp'].dt.strftime('%Y-%m-%d') == today]

        if df_today.empty:
            bot.send_message(chat_id=CHAT_ID, text=f"📊 No signals generated today ({today}).")
            log("📭 No signals to include in today's report.")
            return

        total = len(df_today)
        avg_conf = round(df_today['confidence'].mean(), 2)
        longs = len(df_today[df_today['prediction'] == "LONG"])
        shorts = len(df_today[df_today['prediction'] == "SHORT"])
        normal = len(df_today[df_today['trade_type'] == "Normal"])
        scalp = len(df_today[df_today['trade_type'] == "Scalping"])

        msg = (
            f"📆 *Daily Signal Report - {today}*\n\n"
            f"📈 Total Signals: *{total}*\n"
            f"🎯 Avg Confidence: *{avg_conf}%*\n\n"
            f"🟢 LONGs: `{longs}`\n🔴 SHORTs: `{shorts}`\n"
            f"📊 Normal: `{normal}` | Scalping: `{scalp}`"
        )

        bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode="Markdown")
        log("📤 Daily report sent to Telegram.")

    except Exception as e:
        log(f"❌ Report send error: {e}")
