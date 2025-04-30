import os
from telegram import Bot
from telegram.error import TelegramError
from utils.logger import log
from datetime import datetime

async def send_signal(symbol, signal):
    try:
        bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
        chat_id = os.getenv("TELEGRAM_CHAT_ID")
        
        if not bot_token or not chat_id:
            log("❌ Telegram bot token or chat ID not set")
            return

        bot = Bot(token=bot_token)

        price = signal.get("price", 0)
        direction = signal.get("prediction", "Unknown")
        confidence = signal.get("confidence", 0)
        trade_type = signal.get("trade_type", "Unknown")
        leverage = signal.get("leverage", 20)
        timestamp = datetime.fromtimestamp(signal.get("timestamp", 0) / 1000).strftime('%Y-%m-%d %H:%M:%S')
        tp1 = signal.get("tp1", 0)
        tp2 = signal.get("tp2", 0)
        tp3 = signal.get("tp3", 0)
        sl = signal.get("sl", 0)
        tp1_possibility = signal.get("tp1_possibility", 70)
        tp2_possibility = signal.get("tp2_possibility", 60)
        tp3_possibility = signal.get("tp3_possibility", 50)

        message = (
            f"📊 *Signal for {symbol}*\n"
            f"💰 *Current Price*: {price}\n"
            f"📍 *Entry Price*: {price}\n"  # Added Entry Price
            f"📈 *Direction*: {direction}\n"
            f"🎯 *TP1*: {tp1} ({tp1_possibility}%)\n"
            f"🎯 *TP2*: {tp2} ({tp2_possibility}%)\n"
            f"🎯 *TP3*: {tp3} ({tp3_possibility}%)\n"
            f"🛑 *SL*: {sl}\n"
            f"🔍 *Confidence*: {confidence}%\n"
            f"📉 *Trade Type*: {trade_type}\n"
            f"⚖️ *Leverage*: {leverage}x\n"
        )

        await bot.send_message(chat_id=chat_id, text=message, parse_mode="Markdown")
        log(f"✅ Signal sent to Telegram for {symbol}")
        
    except TelegramError as e:
        log(f"❌ Failed to send Telegram signal for {symbol}: {e}")
    except Exception as e:
        log(f"❌ Unexpected error sending Telegram signal for {symbol}: {e}")
