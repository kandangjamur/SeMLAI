import time
import ccxt
from core.indicators import calculate_indicators
from core.trade_classifier import classify_trade
from core.whale_detector import whale_check
from model.predictor import predict_trend
from telebot.bot import send_signal
from utils.logger import log, log_signal_to_csv  # ✅ Added CSV logger

# ⏳ Memory of last sent signals (symbol → timestamp)
sent_signals = {}

def run_analysis_loop():
    log("📊 Starting Market Scan")
    exchange = ccxt.binance()
    symbols = [s for s in exchange.load_markets() if '/USDT' in s]

    while True:
        try:
            for symbol in symbols:
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                signal = calculate_indicators(symbol, ohlcv)

                if not signal:
                    continue

                # 🚫 Skip low-confidence signals
                if signal['confidence'] < 85:
                    log(f"⏩ Skipped {symbol} due to low confidence ({signal['confidence']}%)")
                    continue

                # 🚫 Prevent duplicate signal within 30 mins
                now = time.time()
                if symbol in sent_signals and now - sent_signals[symbol] < 1800:
                    log(f"🔁 Skipped {symbol} (already sent in last 30 mins)")
                    continue

                # ✅ Whale check
                if not whale_check(symbol, exchange):
                    log(f"🐋 No whale activity on {symbol}, skipped.")
                    continue

                # 🧠 Predict direction
                signal['prediction'] = predict_trend(symbol, ohlcv)

                # 📊 Classify trade
                signal['trade_type'] = classify_trade(signal)

                # 🛡 Spot trades can't be SHORT
                if signal['trade_type'] == "Spot":
                    signal['prediction'] = "LONG"

                # ✅ Save timestamp to memory
                sent_signals[symbol] = now

                # 🧾 Log to CSV before sending
                log_signal_to_csv(signal)  # ✅ Add this line

                # 🚀 Send signal
                log(f"✅ Signal: {symbol} | {signal['trade_type']} | {signal['prediction']} | {signal['confidence']}%")
                send_signal(signal)

        except Exception as e:
            log(f"❌ Analysis Error: {e}")

        time.sleep(120)
