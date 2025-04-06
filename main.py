import time
import os
from flask import Flask, request
from utils.market_analysis import analyze_market
from utils.signal_formatter import format_signal
import requests
import threading

app = Flask(__name__)

# Bot credentials from .env
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ─── Flask Routes ──────────────────────────────────────

@app.route('/ping', methods=['GET'])
def ping():
    return "Pong", 200

@app.route('/get', methods=['GET'])
def get():
    return "Running", 200

@app.route(f'/{TOKEN}', methods=['POST'])
def telegram_webhook():
    data = request.get_json()
    if "message" in data and "text" in data["message"]:
        text = data["message"]["text"]
        chat_id = str(data["message"]["chat"]["id"])
        if chat_id != CHAT_ID:
            return "Unauthorized", 403

        if text == "/status":
            send_to_telegram("✅ Bot is *active* and running.", parse=True)
        elif text == "/manualscan":
            signal = analyze_market()
            if signal:
                send_to_telegram(format_signal(signal), parse=True)
            else:
                send_to_telegram("⚠️ No strong signals found right now.")
    return "OK", 200

# ─── Telegram Send Function ─────────────────────────────

def send_to_telegram(message, parse=False):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": message}
    if parse:
        data["parse_mode"] = "Markdown"
    requests.post(url, data=data)

# ─── Background Analysis ───────────────────────────────

def start_market_analysis():
    while True:
        try:
            signal = analyze_market()
            if signal:
                formatted = format_signal(signal)
                send_to_telegram(formatted, parse=True)
            time.sleep(60)
        except Exception as e:
            print("Error:", e)
            time.sleep(30)

# ─── Start ──────────────────────────────────────────────

if __name__ == '__main__':
    threading.Thread(target=start_market_analysis).start()
    app.run(host='0.0.0.0', port=8000)
