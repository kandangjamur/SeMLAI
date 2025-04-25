from telegram import Bot, ParseMode
from telegram.ext import Updater, CommandHandler
from utils.logger import log
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=BOT_TOKEN)

def send_signal(signal):
    message = (
        f"🚨 *New Signal Detected*\n\n"
        f"*Pair:* `{signal['symbol']}`\n"
        f"*Confidence:* `{signal['confidence']}%`\n"
        f"*Type:* `{signal['trade_type']} ({signal['prediction']})`\n"
        f"*Leverage:* `{signal['leverage']}x`\n"
        f"*TP1:* `{signal['tp1']} ({signal.get('tp1_prob', 'N/A')}%)`\n"
        f"*TP2:* `{signal['tp2']} ({signal.get('tp2_prob', 'N/A')}%)`\n"
        f"*TP3:* `{signal['tp3']} ({signal.get('tp3_prob', 'N/A')}%)`\n"
        f"*SL:* `{signal['sl']}`"
    )
    bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN)

def start_telegram_bot():
    updater = Updater(BOT_TOKEN, use_context=True)
    updater.start_polling()
    log("📲 Telegram bot started")
