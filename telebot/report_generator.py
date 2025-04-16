import csv
from datetime import datetime
from telebot.bot import bot, chat_id
import os

def generate_daily_summary():
    log_file = "logs/signals_log.csv"
    if not os.path.exists(log_file):
        return

    total = 0
    tp1 = tp2 = tp3 = sl = 0
    spot = normal = scalping = 0

    today = datetime.now().strftime("%Y-%m-%d")

    with open(log_file, "r") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not row["timestamp"].startswith(today):
                continue
            total += 1
            status = row["status"]
            ttype = row["trade_type"]

            if status == "TP1":
                tp1 += 1
            elif status == "TP2":
                tp2 += 1
            elif status == "TP3":
                tp3 += 1
            elif status == "SL":
                sl += 1

            if ttype == "Spot":
                spot += 1
            elif ttype == "Normal":
                normal += 1
            elif ttype == "Scalping":
                scalping += 1

    msg = f"""
📊 Daily Sniper Summary ({today})

Total Signals Sent: {total}

🎯 Accuracy Breakdown:
- TP1 Hit: {tp1}
- TP2 Hit: {tp2}
- TP3 Hit: {tp3}
- SL Hit: {sl}

🔍 Signal Type Stats:
- Scalping: {scalping}
- Normal: {normal}
- Spot: {spot}

✅ Overall Success Rate: {round(((tp1 + tp2 + tp3) / total)*100, 2) if total else 0}%
"""

    bot.send_message(chat_id=chat_id, text=msg)
