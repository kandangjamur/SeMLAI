import csv
from datetime import datetime
from telebot.bot import bot, chat_id

def generate_daily_summary():
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = "logs/signals_log.csv"

    total = tp1 = tp2 = tp3 = sl = 0
    scalping = spot = normal = 0

    try:
        with open(log_path, "r") as file:
            reader = csv.DictReader(file)
            for row in reader:
                if today not in row["datetime"]:
                    continue
                total += 1
                if row["type"] == "Scalping":
                    scalping += 1
                elif row["type"] == "Spot":
                    spot += 1
                else:
                    normal += 1

                if row["status"] == "TP1":
                    tp1 += 1
                elif row["status"] == "TP2":
                    tp2 += 1
                elif row["status"] == "TP3":
                    tp3 += 1
                elif row["status"] == "SL":
                    sl += 1

        success = tp1 + tp2 + tp3
        accuracy = round((success / total) * 100, 1) if total > 0 else 0

        msg = (
            f"📅 *Crypto Sniper Daily Report* ({today})\n\n"
            f"Total Signals: {total}\n\n"
            f"By Type:\n"
            f"• Scalping: {scalping}\n"
            f"• Normal: {normal}\n"
            f"• Spot: {spot}\n\n"
            f"🎯 Hits:\n"
            f"• TP1: {tp1}\n"
            f"• TP2: {tp2}\n"
            f"• TP3: {tp3}\n"
            f"❌ SL: {sl}\n\n"
            f"✅ *Success Rate:* {accuracy}%"
        )

        bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")
    except Exception as e:
        print("Report generation error:", e)
