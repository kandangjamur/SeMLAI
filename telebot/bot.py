from telegram import Bot
import os

bot = Bot(token=os.getenv("TELEGRAM_BOT_TOKEN"))
chat_id = os.getenv("TELEGRAM_CHAT_ID")

def send_signal(signal):
    msg = (
        f"🚀 *Crypto Signal*\n\n"
        f"Symbol: {signal['symbol']}\n"
        f"Type: {signal['trade_type']}\n"
        f"Direction: {signal['direction']}\n"
        f"Price: {signal['price']}\n"
        f"Leverage: {signal['leverage']}x\n"
        f"RSI: {signal['rsi']:.2f}\n"
        f"Confidence: {signal['confidence']}%\n\n"
        f"🎯 TP1: {signal['tp1']}\n"
        f"🎯 TP2: {signal['tp2']}\n"
        f"🎯 TP3: {signal['tp3']}\n"
        f"🛑 SL: {signal['sl']}"
    )
    bot.send_message(chat_id=chat_id, text=msg, parse_mode="Markdown")

def start_telegram_bot():
    print("✅ Telegram bot running...")
