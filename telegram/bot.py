from telegram import Bot
import os

bot = Bot(token=os.getenv("7620836100:AAEEe4yAP18Lxxj0HoYfH8aeX4PetAxYsV0"))
chat_id = os.getenv("-4694205383")

def send_signal(signal):
    msg = f"🚀 *Crypto Signal*

"           f"Symbol: {signal['symbol']}
"           f"Type: {signal['trade_type']}
"           f"Direction: {signal['prediction']}
"           f"Price: {signal['price']}
"           f"RSI: {signal['rsi']:.2f}
"           f"Confidence: {signal['confidence']}%"
    bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")

def start_telegram_bot():
    print("✅ Telegram bot running...")
