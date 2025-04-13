import os
import threading
from flask import Flask, jsonify
from binance.client import Client
from core.analysis import analyze_all_symbols
from utils.logger import log
from telegram.bot import run_bot  # ✅ Import Telegram bot starter

# Initialize Binance client
binance_client = Client(
    api_key=os.getenv('BINANCE_API_KEY'),
    api_secret=os.getenv('BINANCE_API_SECRET')
)

# Initialize Flask app
app = Flask(__name__)

def get_all_usdt_pairs(limit=0):
    try:
        exchange_info = binance_client.get_exchange_info()
        all_pairs = [symbol['symbol'] for symbol in exchange_info['symbols'] if symbol['symbol'].endswith('USDT')]
        if limit > 0:
            all_pairs = all_pairs[:limit]
        log(f"Fetched {len(all_pairs)} USDT pairs.")
        return all_pairs
    except Exception as e:
        log(f"Error fetching USDT pairs: {e}")
        return []

@app.route('/status', methods=['GET'])
def status():
    return jsonify({"status": "running"}), 200

@app.route('/manualscan', methods=['GET'])
def manual_scan():
    try:
        symbols = get_all_usdt_pairs(limit=50)
        if not symbols:
            return jsonify({"status": "error", "message": "No USDT pairs found."}), 500

        log("Starting signal analysis on USDT pairs...")

        signals = analyze_all_symbols(symbols)

        if signals:
            log(f"{len(signals)} valid signals found.")
            for sig in signals:
                log(f"✅ {sig['symbol']} ({sig['timeframe']}): Confidence {sig['confidence']}% | Score {sig['score']}")
            return jsonify({"signals": signals}), 200
        else:
            log("No valid signals found.")
            return jsonify({"message": "No valid signals found."}), 200
    except Exception as e:
        log(f"Error in /manualscan: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    threading.Thread(target=run_bot).start()  # ✅ START TELEGRAM BOT FIRST
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)  # ✅ THEN START FLASK
