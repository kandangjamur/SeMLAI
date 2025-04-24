from telegram import Bot, ParseMode
from telegram.ext import Updater, CommandHandler
from utils.logger import log
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=BOT_TOKEN)

def send_signal(signal):
    message = (
        f"🚨 *Crypto Signal Alert*\n\n"
        f"🪙 *Symbol:* `{signal['symbol']}`\n"
        f"📈 *Direction:* {signal['prediction']}\n"
        f"💹 *Entry:* {signal['price']}\n"
        f"🎯 *TP1:* {signal['tp1']} ({signal['tp1_chance']}%)\n"
        f"🎯 *TP2:* {signal['tp2']} ({signal['tp2_chance']}%)\n"
        f"🎯 *TP3:* {signal['tp3']} ({signal['tp3_chance']}%)\n"
        f"🛡 *SL:* {signal['sl']}\n"
        f"📊 *Confidence:* {signal['confidence']}%\n"
        f"⚙️ *Leverage:* {signal['leverage']}x\n"
        f"🔖 *Type:* {signal['trade_type']}"
    )

    try:
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode=ParseMode.MARKDOWN)
        log(f"📤 Sent to Telegram: {signal['symbol']}")
    except Exception as e:
        log(f"❌ Telegram Error: {e}")

def start_telegram_bot():
    try:
        updater = Updater(BOT_TOKEN, use_context=True)
        dispatcher = updater.dispatcher

        def status(update, context):
            update.message.reply_text("✅ Crypto Sniper is running...")

        dispatcher.add_handler(CommandHandler("status", status))
        updater.start_polling()
        log("🤖 Telegram bot started.")
    except Exception as e:
        log(f"❌ Telegram Bot Error: {e}")
