import os
from dotenv import load_dotenv
from telegram import Bot, ParseMode, Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from utils.logger import log

# Load .env
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Bot init
bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

# ✅ Signal Sender
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

# ✅ Commands

def manual_report(update: Update, context: CallbackContext):
    try:
        from telebot.report_generator import generate_daily_summary
        generate_daily_summary()
        update.message.reply_text("📊 Manual daily report generated.")
    except Exception as e:
        update.message.reply_text(f"❌ Error: {e}")
        log(f"❌ Manual report error: {e}")

def manual_backtest(update: Update, context: CallbackContext):
    try:
        from core.backtester import run_backtest_report
        run_backtest_report()
        update.message.reply_text("📈 Backtest report triggered.")
    except Exception as e:
        update.message.reply_text(f"❌ Error: {e}")
        log(f"❌ Manual backtest error: {e}")

def status_check(update: Update, context: CallbackContext):
    try:
        update.message.reply_text("✅ Crypto Sniper Bot is running!")
    except Exception as e:
        log(f"❌ Status error: {e}")

def manual_scan(update: Update, context: CallbackContext):
    try:
        from core.analysis import run_analysis_once
        run_analysis_once()
        update.message.reply_text("🔍 Manual market scan triggered.")
    except Exception as e:
        update.message.reply_text(f"❌ Error: {e}")
        log(f"❌ Manual scan error: {e}")

# ✅ This function must exist and be top-level (important)
def start_telegram_bot():
    try:
        dispatcher.add_handler(CommandHandler("manualreport", manual_report))
        dispatcher.add_handler(CommandHandler("backtest", manual_backtest))
        dispatcher.add_handler(CommandHandler("status", status_check))
        dispatcher.add_handler(CommandHandler("manualscan", manual_scan))
        updater.start_polling()
        log("✅ Telegram bot is active (send_signal & commands ready)")
    except Exception as e:
        log(f"❌ Telegram Bot Init Error: {e}")
