import httpx
import asyncio
import pandas as pd
import os
from datetime import datetime
from utils.logger import log

BOT_TOKEN = "7620836100:AAEEe4yAP18Lxxj0HoYfH8aeX4PetAxYsV0"
CHAT_ID = "-4694205383"
ADMIN_CHAT_ID = "-1234567890"  # Replace with your admin chat ID

async def send_telegram_signal(symbol: str, signal: dict):
    try:
        direction = signal.get("direction", "Unknown")
        confidence = signal.get("confidence", 0)
        price = signal.get("price", 0)
        tp1 = signal.get("tp1", 0)
        tp2 = signal.get("tp2", 0)
        tp3 = signal.get("tp3", 0)
        sl = signal.get("sl", 0)
        tp1_possibility = signal.get("tp1_possibility", 0)
        tp2_possibility = signal.get("tp2_possibility", 0)
        tp3_possibility = signal.get("tp3_possibility", 0)
        leverage = signal.get("leverage", 10)

        message = (
            f"🚀 *{symbol} Signal*\n\n"
            f"📊 *Direction*: {direction}\n"
            f"💰 *Entry Price*: {price:.4f}\n"
            f"🎯 *TP1*: {tp1:.4f} ({tp1_possibility}%)\n"
            f"🎯 *TP2*: {tp2:.4f} ({tp2_possibility}%)\n"
            f"🎯 *TP3*: {tp3:.4f} ({tp3_possibility}%)\n"
            f"🛑 *SL*: {sl:.4f}\n"
            f"⚖️ *Leverage*: {leverage}x\n"
            f"🔍 *Confidence*: {confidence:.2f}%\n"
            f"🕒 *Timestamp*: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }

        async with httpx.AsyncClient() as client:
            for attempt in range(3):
                try:
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        log(f"Telegram signal sent for {symbol}")
                        log_telegram_status(symbol, True, "Success")
                        return
                    else:
                        log(f"Failed to send Telegram signal for {symbol}: {response.text}", level='ERROR')
                        log_telegram_status(symbol, False, response.text)
                except Exception as e:
                    log(f"Error sending Telegram signal for {symbol}: {e}", level='ERROR')
                    log_telegram_status(symbol, False, str(e))
                await asyncio.sleep(2)

            # Send admin alert on failure
            admin_message = f"⚠️ *Emergency Alert*: Failed to send signal for {symbol} after 3 attempts."
            admin_payload = {
                "chat_id": ADMIN_CHAT_ID,
                "text": admin_message,
                "parse_mode": "Markdown"
            }
            try:
                await client.post(url, json=admin_payload)
                log(f"Admin alert sent for {symbol} Telegram failure")
            except Exception as e:
                log(f"Failed to send admin alert for {symbol}: {e}", level='ERROR')

    except Exception as e:
        log(f"Error in send_telegram_signal for {symbol}: {e}", level='ERROR')
        log_telegram_status(symbol, False, str(e))

def log_telegram_status(symbol: str, success: bool, message: str):
    try:
        csv_path = "logs/telegram_status.csv"
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        data = {
            "symbol": symbol,
            "success": success,
            "message": message,
            "timestamp": timestamp
        }
        df = pd.DataFrame([data])

        if os.path.exists(csv_path):
            old_df = pd.read_csv(csv_path)
            if not df.empty and not df.isna().all().all():
                df = pd.concat([old_df, df], ignore_index=True)

        if not df.empty and not df.isna().all().all():
            df.to_csv(csv_path, index=False)
            log(f"Telegram status logged for {symbol}: Success={success}")
        else:
            log("No valid data to log Telegram status", level='ERROR')
    except Exception as e:
        log(f"Error logging Telegram status for {symbol}: {e}", level='ERROR')
