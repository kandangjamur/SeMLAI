import pandas as pd
from datetime import datetime
from utils.logger import log
from telebot.bot import bot, CHAT_ID

def generate_daily_summary():
    try:
        df = pd.read_csv("logs/signals_log.csv")
        today = datetime.now().date()
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms', errors='coerce')
        df_today = df[df['timestamp'].dt.date == today]

        total = len(df_today)
        tp1_hits = len(df_today[df_today['status'] == 'tp1'])
        tp2_hits = len(df_today[df_today['status'] == 'tp2'])
        tp3_hits = len(df_today[df_today['status'] == 'tp3'])
        sl_hits = len(df_today[df_today['status'] == 'sl'])

        summary = (
            f"📊 *Daily Summary ({today})*\n\n"
            f"📌 Total Signals: {total}\n"
            f"🎯 TP1 Hits: {tp1_hits}\n"
            f"🎯 TP2 Hits: {tp2_hits}\n"
            f"🎯 TP3 Hits: {tp3_hits}\n"
            f"🛡 SL Hits: {sl_hits}\n"
        )

        bot.send_message(chat_id=CHAT_ID, text=summary, parse_mode="Markdown")
        log("📬 Daily report sent.")
    except Exception as e:
        log(f"❌ Report Error: {e}")
