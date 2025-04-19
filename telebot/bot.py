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
        leverage = signal.get("leverage", "-")
        tp1 = signal.get("tp1", "-")
        tp2 = signal.get("tp2", "-")
        tp3 = signal.get("tp3", "-")
        sl = signal.get("sl", "-")

        msg = (
            f"📊 *Crypto Sniper Signal*\n"
            f"*{signal['symbol']}*\n\n"
            f"*Direction:* `{signal['prediction']}`\n"
            f"*Confidence:* `{signal['confidence']}%`\n"
            f"*Type:* `{signal['trade_type']}`\n"
            f"*Leverage:* `{leverage}x`\n"
            f"*Price:* `{signal['price']}`\n\n"
            f"🎯 *TP1:* `{tp1}`\n"
            f"🎯 *TP2:* `{tp2}`\n"
            f"🎯 *TP3:* `{tp3}`\n"
            f"🛡 *SL:* `{sl}`"
        )
        bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
        log(f"📨 Telegram sent: {signal['symbol']}")
    except Exception as e:
        log(f"❌ Telegram Send Error: {e}")
