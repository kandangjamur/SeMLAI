import pandas as pd
from datetime import datetime
from utils.logger import log

def generate_daily_summary():
    try:
        df = pd.read_csv("logs/signals_log.csv")
        today = datetime.now().date()
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        today_signals = df[df['timestamp'].dt.date == today]

        total = len(today_signals)
        tp1_hits = len(today_signals[today_signals['status'] == 'tp1'])
        tp2_hits = len(today_signals[today_signals['status'] == 'tp2'])
        tp3_hits = len(today_signals[today_signals['status'] == 'tp3'])
        sl_hits = len(today_signals[today_signals['status'] == 'sl'])

        summary = (
            f"📊 *Daily Summary ({today})*\n\n"
            f"📌 Total Signals: {total}\n"
            f"🎯 TP1 Hits: {tp1_hits}\n"
            f"🎯 TP2 Hits: {tp2_hits}\n"
            f"🎯 TP3 Hits: {tp3_hits}\n"
            f"🛡 SL Hits: {sl_hits}\n"
        )

        from telebot.bot import bot, CHAT_ID
        bot.send_message(chat_id=CHAT_ID, text=summary, parse_mode="Markdown")
        log("📬 Daily report sent.")
    except Exception as e:
        log(f"❌ Report Error: {e}")
