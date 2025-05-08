import httpx
import asyncio
from datetime import datetime
import pytz
from utils.logger import log

BOT_TOKEN = "7620836100:AAEEe4yAP18Lxxj0HoYfH8aeX4PetAxYsV0"
CHAT_ID = "-4694205383"

async def send_telegram_signal(symbol: str, signal: dict):
    try:
        direction = signal.get("direction", "Unknown")
        confidence = signal.get("confidence", 0)
        price = signal.get("entry", 0)
        tp1 = signal.get("tp1", 0)
        tp2 = signal.get("tp2", 0)
        tp3 = signal.get("tp3", 0)
        sl = signal.get("sl", 0)
        tp1_possibility = 0.75  # ڈمی ویلیو، core/analysis.py میں شامل کرو تو یہ ہٹائیں
        trade_type = "Scalping" if confidence < 85 else "Normal"

        message = (
            f"🚀 *{symbol} Signal*\n\n"
            f"📊 *Direction*: {direction}\n"
            f"💰 *Entry Price*: {price:.4f}\n"
            f"🎯 *TP1*: {tp1:.4f} ({tp1_possibility:.2f}%)\n"
            f"🎯 *TP2*: {tp2:.4f}\n"
            f"🎯 *TP3*: {tp3:.4f}\n"
            f"🛑 *SL*: {sl:.4f}\n"
            f"🔍 *Confidence*: {confidence:.2f}%\n"
            f"⚡ *Trade Type*: {trade_type}\n"
            f"🕒 *Timestamp*: {datetime.now(pytz.timezone('Asia/Karachi')).strftime('%Y-%m-%d %H:%M:%S')}"
        )

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient() as client:
            for attempt in range(3):
                try:
                    payload = {
                        "chat_id": CHAT_ID,
                        "text": message,
                        "parse_mode": "Markdown"
                    }
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        log(f"Telegram signal sent for {symbol}")
                        return
                    else:
                        log(f"Failed to send Telegram signal: {response.text}", level='ERROR')
                except Exception as e:
                    log(f"Error sending Telegram signal: {e}", level='ERROR')
                await asyncio.sleep(2)

    except Exception as e:
        log(f"Error in send_telegram_signal: {e}", level='ERROR')
