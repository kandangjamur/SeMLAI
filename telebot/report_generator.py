import pandas as pd
from datetime import datetime
from telebot.bot import bot
from utils.logger import log

def generate_daily_summary():
    try:
        df = pd.read_csv("logs/signals_log.csv")
        today = datetime.now().strftime("%Y-%m-%d")
        today_df = df[df["timestamp"].str.contains(today)]

        total = len(today_df)
        tp1 = len(today_df[today_df["status"] == "TP1"])
        tp2 = len(today_df[today_df["status"] == "TP2"])
        tp3 = len(today_df[today_df["status"] == "TP3"])
        sl = len(today_df[today_df["status"] == "SL"])
        open_ = len(today_df[today_df["status"] == "OPEN"])

        msg = (
            f"📅 *Daily Report* - {today}\n"
            f"Total Signals: `{total}`\n"
            f"TP1 Hit: `{tp1}`\n"
            f"TP2 Hit: `{tp2}`\n"
            f"TP3 Hit: `{tp3}`\n"
            f"SL Hit: `{sl}`\n"
            f"Open: `{open_}`"
        )
        bot.send_message(chat_id=os.getenv("TELEGRAM_CHAT_ID"), text=msg, parse_mode="Markdown")
        log("📩 Daily report sent to Telegram")
    except Exception as e:
        log(f"❌ Report error: {e}")
