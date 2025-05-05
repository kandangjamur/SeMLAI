import httpx
import asyncio
import pandas as pd
import os
from datetime import datetime
import pytz
from utils.logger import log

BOT_TOKEN = "7620836100:AAEEe4yAP18Lxxj0HoYfH8aeX4PetAxYsV0"
CHAT_ID = "-4694205383"

signal_queue = []
last_signal_time = 0
MIN_SIGNAL_GAP = 30  # 30 seconds between signals

async def send_telegram_signal(symbol: str, signal: dict):
    global signal_queue, last_signal_time
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
        trade_type = signal.get("trade_type", "Scalping")
        indicators_used = signal.get("indicators_used", "N/A")
        backtest_result = signal.get("backtest_result", 0)

        message = (
            f"🚀 *{symbol} Signal*\n\n"
            f"📊 *Direction*: {direction}\n"
            f"💰 *Entry Price*: {price:.4f}\n"
            f"🎯 *TP1*: {tp1:.4f} ({tp1_possibility:.2f}%)\n"
            f"🎯 *TP2*: {tp2:.4f} ({tp2_possibility:.2f}%)\n"
            f"🎯 *TP3*: {tp3:.4f} ({tp3_possibility:.2f}%)\n"
            f"🛑 *SL*: {sl:.4f}\n"
            f"⚖️ *Leverage*: {leverage}x\n"
            f"🔍 *Confidence*: {confidence:.2f}%\n"
            f"📡 *Indicators*: {indicators_used}\n"
            f"✅ *Backtest TP1 Hit*: {backtest_result:.2f}%\n"
            f"⚡ *Trade Type*: {trade_type}\n"
            f"🕒 *Timestamp*: {datetime.now(pytz.timezone('Asia/Karachi')).strftime('%Y-%m-%d %H:%M:%S')}"
        )

        signal_queue.append({"symbol": symbol, "message": message})
        
        current_time = datetime.now().timestamp()
        if current_time - last_signal_time < MIN_SIGNAL_GAP or len(signal_queue) < 2:
            return
        
        # Batch send signals
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        async with httpx.AsyncClient() as client:
            for signal in signal_queue[:2]:  # Max 2 signals per minute
                payload = {
                    "chat_id": CHAT_ID,
                    "text": signal["message"],
                    "parse_mode": "Markdown"
                }
                for attempt in range(3):
                    try:
                        response = await client.post(url, json=payload)
                        if response.status_code == 200:
                            log(f"Telegram signal sent for {signal['symbol']}")
                            break
                        else:
                            log(f"Failed to send Telegram signal: {response.text}", level='ERROR')
                    except Exception as e:
                        log(f"Error sending Telegram signal: {e}", level='ERROR')
                    await asyncio.sleep(2)
        
        signal_queue.clear()
        last_signal_time = current_time

    except Exception as e:
        log(f"Error in send_telegram_signal: {e}", level='ERROR')
