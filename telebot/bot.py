import os
import telegram
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
bot = telegram.Bot(token=BOT_TOKEN)

def send_signal(signal):
    message = (
        f"🚀 Signal: {signal['symbol']}\n"
        f"🧠 Confidence: {signal['confidence']}%\n"
        f"📈 Direction: {signal['prediction']}\n"
        f"📊 Type: {signal['trade_type']}\n"
        f"📍 Entry: ${signal['price']}\n"
        f"🎯 TP1: ${signal['tp1']} ({signal['tp1_possibility']}%)\n"
        f"🎯 TP2: ${signal['tp2']} ({signal['tp2_possibility']}%)\n"
        f"🎯 TP3: ${signal['tp3']} ({signal['tp3_possibility']}%)\n"
        f"🛡 SL: ${signal['sl']}\n"
        f"⚙️ Leverage: {signal['leverage']}x"
    )
    bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")

def start_telegram_bot():
    print("📲 Telegram bot started")
