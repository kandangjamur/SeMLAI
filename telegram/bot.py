import os
import threading
from telegram import Bot, Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from dotenv import load_dotenv
from core.analysis import analyze_market
from telegram.report_generator import format_signal
from utils.logger import log

load_dotenv()

TELEGRAM_TOKEN = os.getenv("7620836100:AAEEe4yAP18Lxxj0HoYfH8aeX4PetAxYsV0")
CHAT_ID = os.getenv("-4694205383")

bot = Bot(token=TELEGRAM_TOKEN)
updater = Updater(token=TELEGRAM_TOKEN, use_context=True)
dispatcher = updater.dispatcher


def send_signal(signal):
    try:
        message = format_signal(signal)
        bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="HTML")
        log(f"✅ Signal sent for {signal['symbol']}")
    except Exception as e:
        log(f"❌ Error sending signal: {e}")


def auto_signal_loop():
    import time
    while True:
        try:
            signals = analyze_market()
            for signal in signals:
                send_signal(signal)
            time.sleep(300)  # run every 5 minutes
        except Exception as e:
            log(f"Auto-signal loop error: {e}")
            time.sleep(60)


def status(update: Update, context: CallbackContext):
    update.message.reply_text("✅ Bot is running and scanning the market.")


def manual_scan(update: Update, context: CallbackContext):
    update.message.reply_text("🔍 Running manual scan...")
    try:
        signals = analyze_market()
        if not signals:
            update.message.reply_text("⚠️ No strong signals at the moment.")
        else:
            for signal in signals:
                send_signal(signal)
    except Exception as e:
        update.message.reply_text(f"❌ Error: {e}")
        log(f"Manual scan error: {e}")


def run_bot():
    dispatcher.add_handler(CommandHandler("status", status))
    dispatcher.add_handler(CommandHandler("manualscan", manual_scan))

    updater.start_polling()
    log("📡 Telegram bot started.")
    threading.Thread(target=auto_signal_loop).start()
