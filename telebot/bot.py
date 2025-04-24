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
            f"📊 *Crypto Sniper Signal*\n"
            f"*{signal['symbol']}*\n\n"
            f"📈 Direction: `{signal['prediction']}`\n"
            f"🔥 Confidence: `{signal['confidence']}%`\n"
            f"🎯 Type: `{signal['trade_type']}`\n"
            f"⚡ Leverage: `{signal['leverage']}x`\n"
            f"💰 Entry: `{signal['price']}`\n\n"
            f"🎯 TP1: `{signal['tp1']}` ({signal['tp1_chance']}%)\n"
            f"🎯 TP2: `{signal['tp2']}` ({signal['tp2_chance']}%)\n"
            f"🎯 TP3: `{signal['tp3']}` ({signal['tp3_chance']}%)\n"
            f"🛡 SL: `{signal['sl']}`\n\n"
            f"🧱 Support: `{signal.get('support', '-')}`\n"
            f"🧱 Resistance: `{signal.get('resistance', '-')}`"
        )
        bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
        log(f"📨 Signal sent: {signal['symbol']}")
    except Exception as e:
        log(f"❌ Telegram Send Error: {e}")

# Optional commands
def manual_report(update: Update, context: CallbackContext):
    from telebot.report_generator import generate_daily_summary
    try:
        generate_daily_summary()
        update.message.reply_text("📊 Daily report sent.")
    except Exception as e:
        update.message.reply_text(f"❌ Report error: {e}")
        log(f"❌ Manual report error: {e}")

def manual_scan(update: Update, context: CallbackContext):
    from core.analysis import run_analysis_once
    try:
        run_analysis_once()
        update.message.reply_text("🔁 Manual scan started.")
    except Exception as e:
        update.message.reply_text(f"❌ Scan error: {e}")
        log(f"❌ Manual scan error: {e}")

def start_telegram_bot():
    try:
        dispatcher.add_handler(CommandHandler("manualreport", manual_report))
        dispatcher.add_handler(CommandHandler("manualscan", manual_scan))
        updater.start_polling()
        log("✅ Telegram bot ready.")
    except Exception as e:
        log(f"❌ Telegram Bot Init Error: {e}")
