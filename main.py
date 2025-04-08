import os
from flask import Flask, jsonify
from binance.client import Client
from core.analysis import analyze_all_symbols
from utils.logger import log

# Initialize Binance client
binance_client = Client(
    api_key=os.getenv('BINANCE_API_KEY'),
    api_secret=os.getenv('BINANCE_API_SECRET')
)

# Initialize Flask app
app = Flask(__name__)

# Function to fetch all USDT pairs from Binance
def get_all_usdt_pairs():
    try:
        exchange_info = binance_client.get_exchange_info()
        symbols = [symbol['symbol'] for symbol in exchange_info['symbols'] if symbol['symbol'].endswith('USDT')]
        return symbols
    except Exception as e:
        log(f"Error fetching USDT pairs: {e}")
        return []

@app.route('/status', methods=['GET'])
def status():
    try:
        return jsonify({"status": "running"}), 200
    except Exception as e:
        log(f"Error in /status: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route('/manualscan', methods=['GET'])
def manual_scan():
    try:
        # Fetch all USDT pairs dynamically
        symbols = get_all_usdt_pairs()

        if not symbols:
            return jsonify({"status": "error", "message": "No USDT pairs found."}), 500

        # Run the analysis on all symbols
        signals = analyze_all_symbols(symbols)

        if signals:
            return jsonify({"signals": signals}), 200
        else:
            return jsonify({"message": "No valid signals found."}), 200
    except Exception as e:
        log(f"Error in /manualscan: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500

if __name__ == "__main__":
    import os
port = int(os.environ.get("PORT", 8000))
app.run(host="0.0.0.0", port=port, debug=True)

