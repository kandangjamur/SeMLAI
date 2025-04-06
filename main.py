import time
import os
from flask import Flask
from utils.market_analysis import analyze_market
from utils.signal_formatter import format_signal
import requests
import threading

app = Flask(__name__)

@app.route('/ping', methods=['GET'])
def ping():
    return "Pong", 200

@app.route('/get', methods=['GET'])
def get():
    return "Running", 200

@app.route('/signal', methods=['GET'])  # Manual test route
def test_signal():
    signal = analyze_market()
    if signal:
        formatted = format_signal(signal)
        send_to_telegram(formatted)
        return "Signal sent", 200
    return "No valid signal found", 200

def send_to_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})

def start_market_analysis():
    while True:
        try:
            signal = analyze_market()
            if signal:
                formatted = format_signal(signal)
                send_to_telegram(formatted)
            time.sleep(60)  # Every 1 min
        except Exception as e:
            print("Error:", e)
            time.sleep(30)

if __name__ == '__main__':
    threading.Thread(target=start_market_analysis).start()
    app.run(host='0.0.0.0', port=8000)
