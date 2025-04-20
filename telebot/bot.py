import os
from dotenv import load_dotenv
from telegram import Bot, ParseMode, Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from utils.logger import log

# Load environment variables
load_dotenv()
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# Initialize Bot and Updater
bot = Bot(token=TOKEN)
updater = Updater(token=TOKEN, use_context=True)
dispatcher = updater.dispatcher

def send_signal(signal: dict):
    """
    Send a formatted signal message to the configured Telegram chat.
    """
    try:
        msg = (
            f"📊 *Crypto Sniper Signal*\n"
            f"*{signal['symbol']}*\n\n"
            f"📈 Direction: `{signal['prediction']}`\n"
            f"🔥 Confidence: `{signal['confidence']}%`\n"
            f"🎯 Type: `{signal['trade_type']}`\n"
            f"⚡ Leverage: `{signal.get('leverage', '-') }x`\n"
            f"💰 Entry: `{signal['price']}`\n\n"
            f"🎯 TP1: `{signal.get('tp1', '-')}`\n"
            f"🎯 TP2: `{signal.get('tp2', '-')}`\n"
            f"🎯 TP3: `{signal.get('tp3', '-')}`\n"
            f"🛡 SL: `{signal.get('sl', '-')}`"
        )
        bot.send_message(chat_id=CHAT_ID, text=msg, parse_mode=ParseMode.MARKDOWN)
        log(f"📨 Signal sent: {signal['symbol']}")
    except Exception as e:
        log(f"❌ Telegram Send Error: {e}")

# ── Command Handlers ──────────────────────────────────────────────────────────

def manual_report(update: Update, context: CallbackContext):
    """
    /manualreport → generate and send the daily summary immediately
    """
    try:
        from telebot.report_generator import generate_daily_summary
        generate_daily_summary()
        update.message.reply_text("📊 Daily report generated.")
    except Exception as e:
        update.message.reply_text(f"❌ Error: {e}")
        log(f"❌ Manual report error: {e}")

def manual_backtest(update: Update, context: CallbackContext):
    """
    /backtest → run backtester and notify when done
    """
    try:
        from core.backtester import run_backtest_report
        run_backtest_report()
        update.message.reply_text("📈 Backtest completed.")
    except Exception as e:
        update.message.reply_text(f"❌ Error: {e}")
        log(f"❌ Manual backtest error: {e}")

def status(update: Update, context: CallbackContext):
    """
    /status → check if the bot is up
    """
    update.message.reply_text("✅ Crypto Sniper is running.")

def manual_scan(update: Update, context: CallbackContext):
    """
    /manualscan → trigger a one-off market scan
    """
    try:
        from core.analysis import run_analysis_once
        run_analysis_once()
        update.message.reply_text("🔁 Manual market scan started.")
    except Exception as e:
        update.message.reply_text(f"❌ Error: {e}")
        log(f"❌ Manual scan error: {e}")

# ── Bot Initialization ────────────────────────────────────────────────────────

def start_telegram_bot():
    """
    Initialize Telegram polling, register commands, and delete any existing webhook.
    """
    try:
        # Remove any active webhook to allow getUpdates polling
        bot.delete_webhook()

        # Register command handlers
        dispatcher.add_handler(CommandHandler("manualreport", manual_report))
        dispatcher.add_handler(CommandHandler("backtest", manual_backtest))
        dispatcher.add_handler(CommandHandler("status", status))
        dispatcher.add_handler(CommandHandler("manualscan", manual_scan))

        # Start polling loop
        updater.start_polling()
        log("✅ Telegram bot ready with commands: /status, /manualreport, /backtest, /manualscan")
    except Exception as e:
        log(f"❌ Telegram Bot Init Error: {e}")
