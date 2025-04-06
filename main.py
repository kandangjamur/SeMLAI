import time
import os
from flask import Flask
from utils.market_analysis import analyze_market
from utils.signal_formatter import format_signal  # Corrected the import
import requests
import threading

app = Flask(__name__)

# Flask route for health check (ping)
@app.route('/ping', methods=['GET'])
def ping():
    return "Pong", 200  # Basic ping route for health check

@app.route('/get', methods=['GET'])
def get():
    return "Running", 200  # Route to indicate the app is running

def send_to_telegram(message):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})

# Function to handle market analysis and telegram updates
def start_market_analysis():
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

if __name__ == '__main__':
    # Start the market analysis in a separate thread
    analysis_thread = threading.Thread(target=start_market_analysis)
    analysis_thread.start()

    # Start the Flask app (HTTP server)
    app.run(host='0.0.0.0', port=8000)  # Ensure that Flask runs on port 8000 for health check
