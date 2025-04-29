import os
import requests

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

def send_signal(signal):
    if not TOKEN or not CHAT_ID:
        print("Telegram token or chat ID missing.")
        return

    message = (
        f"📈 Signal Alert\n\n"
        f"Symbol: {signal['symbol']}\n"
        f"Type: {signal['trade_type']}\n"
        f"Direction: {signal['prediction']}\n"
        f"Entry: {signal['price']}\n"
        f"TP1: {signal['tp1']} ({signal['tp1_possibility']}%)\n"
        f"TP2: {signal['tp2']} ({signal['tp2_possibility']}%)\n"
        f"TP3: {signal['tp3']} ({signal['tp3_possibility']}%)\n"
        f"SL: {signal['sl']}\n"
        f"Confidence: {signal['confidence']}%\n"
        f"Leverage: {signal['leverage']}x"
    )

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }

    try:
        requests.post(url, data=payload)
    except Exception as e:
        print(f"Telegram send error: {e}")
