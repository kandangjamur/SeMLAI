import time
import os
from flask import Flask
from utils.market_analysis import analyze_market
from utils.signal_formatter import format_signal
import threading

app = Flask(__name__)

# This route is for health checks to pass
@app.route('/')
def health_check():
    return 'Bot is running', 200

def send_to_telegram(message):
    import requests
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})

def run_bot():
    while True:
        try:
            signal = analyze_market()  # Assuming this function returns the market signal
            if signal:
                formatted = format_signal(signal)  # Format the signal before sending it
                send_to_telegram(formatted)  # Send the formatted signal to Telegram
            time.sleep(60)  # Scan every 1 min
        except Exception as e:
            print("Error:", e)
            time.sleep(30)  # Wait before retrying in case of error

# Run bot in a separate thread
bot_thread = threading.Thread(target=run_bot)
bot_thread.daemon = True
bot_thread.start()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000)  # Flask app running on port 8000
