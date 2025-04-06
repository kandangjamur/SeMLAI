import time
from utils.market_analysis import analyze_market
from signal_formatter import format_signal

def send_to_telegram(message):
    import requests
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    requests.post(url, data={"chat_id": chat_id, "text": message, "parse_mode": "Markdown"})

while True:
    try:
        signal = analyze_market()
        if signal:
            formatted = format_signal(signal)
            send_to_telegram(formatted)
        time.sleep(60)  # Scan every 1 min
    except Exception as e:
        print("Error:", e)
        time.sleep(30)
