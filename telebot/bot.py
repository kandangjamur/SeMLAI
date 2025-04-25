import os
import telegram
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = telegram.Bot(token=BOT_TOKEN)

def send_signal(signal):
    message = (
        f"🚀 *{signal['symbol']}* Signal Alert\n\n"
        f"🔹 Type: {signal['trade_type']}\n"
        f"🔹 Direction: {signal['prediction']}\n"
        f"📊 Confidence: *{signal['confidence']}%*\n"
        f"🎯 TP1: `{signal['tp1']}`\n"
        f"🎯 TP2: `{signal['tp2']}`\n"
        f"🎯 TP3: `{signal['tp3']}`\n"
        f"🛡 SL: `{signal['sl']}`\n"
        f"📉 Entry: `{signal['price']}`\n"
        f"📈 Leverage: {signal['leverage']}x\n"
    )
    bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")

def start_telegram_bot():
    print("📲 Telegram bot started")
