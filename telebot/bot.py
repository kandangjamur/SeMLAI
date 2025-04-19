import os
from dotenv import load_dotenv
from telegram import Bot, ParseMode, Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from utils.logger import log

load_dotenv()

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

def send_signal(signal):
    try:
        msg = (
            f"🚀 *Crypto Signal*\n"
            f"*{signal['symbol']}*\n\n"
            f"📊 Type: `{signal['trade_type']}`\n"
            f"📈 Direction: *{signal['prediction']}*\n"
            f"🔐 Confidence: *{signal['confidence']}%*\n"
            f"⚡ Leverage: `{signal.get('leverage', '-')}`\n"
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

def start_telegram_bot():
    log("✅ Telegram bot is active (send_signal is ready).")
    updater.start_polling()

# ✅ /manualreport command
def manual_report(update: Update, context: CallbackContext):
    try:
        from telebot.report_generator import generate_daily_summary
        generate_daily_summary()
        context.bot.send_message(chat_id=update.effective_chat.id, text="📊 Manual daily report generated.")
    except Exception as e:
        log(f"❌ Manual report error: {e}")
        context.bot.send_message(chat_id=update.effective_chat.id, text=f"Error generating report: {e}")

# Register command
dispatcher.add_handler(CommandHandler("manualreport", manual_report))
