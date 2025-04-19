import os
from dotenv import load_dotenv
from telegram import Bot, ParseMode
from utils.logger import log

load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TOKEN)

def send_signal(signal):
    try:
        msg = (
            f"🚨 *Crypto Signal Alert*\n"
            f"*{signal['symbol']}*\n\n"
            f"📉 Direction: *{signal['prediction']}*\n"
            f"📊 Confidence: *{signal['confidence']}%*\n"
            f"💼 Type: `{signal['trade_type']}`\n"
            f"⚙️ Leverage: `{signal.get('leverage', '-')}`\n"
            f"💰 Price: `{signal['price']}`\n\n"
            f"🎯 TP1: `{signal['tp1']}`\n"
            f"🎯 TP2: `{signal['tp2']}`\n"
            f"🎯 TP3: `{signal['tp3']}`\n"
            f"🛡 SL: `{signal['sl']}`"
        )
        bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
        log(f"📩 Telegram sent: {signal['symbol']}")
    except Exception as e:
        log(f"❌ Telegram Send Error: {e}")
