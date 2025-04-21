import time
import ccxt
from core.indicators import calculate_indicators
from model.predictor import predict_trend
from telebot.bot import send_signal
from utils.logger import log, log_signal_to_csv
from data.tracker import update_signal_status

sent_signals = {}

def run_analysis_loop():
    log("📊 Starting Market Scan")
    exchange = ccxt.binance()
    symbols = [s for s in exchange.load_markets() if "/USDT" in s]

    while True:
        log("🔁 New Scan Cycle")
        for symbol in symbols:
            log(f"🔍 Scanning: {symbol}")
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                signal = calculate_indicators(symbol, ohlcv)
                if not signal:
                    continue

                # Log base confidence
                log(f"🧠 Base Confidence: {signal['confidence']}% | Type: {signal['trade_type']}")

                # Reject weak TP2 potential
                if signal["tp2"] - signal["price"] < 0.015:
                    log(f"⚠️ Skipped {symbol} - Weak TP2 margin")
                    continue

                # S/R Filtering Logic
                support = signal.get("support")
                resistance = signal.get("resistance")
                price = signal["price"]
                atr = signal.get("atr", 0)
                direction = signal["prediction"]
                buffer = atr * 1.5 if atr else price * 0.01

                if direction == "LONG":
                    if resistance and resistance - price > buffer:
                        signal["confidence"] += 5
                        log("📈 S/R Boost: Price well below resistance ✅")
                    else:
                        log(f"⛔ Skipped {symbol} - Too close to resistance")
                        continue

                elif direction == "SHORT":
                    if support and price - support > buffer:
                        signal["confidence"] += 5
                        log("📉 S/R Boost: Price well above support ✅")
                    else:
                        log(f"⛔ Skipped {symbol} - Too close to support")
                        continue

                # Final confidence log
                log(f"🧠 Final Confidence: {signal['confidence']}%")

                # Skip duplicate within 30 mins
                if symbol in sent_signals and time.time() - sent_signals[symbol] < 1800:
                    continue

                # Predict direction
                signal['prediction'] = predict_trend(symbol, ohlcv)
                log_signal_to_csv(signal)
                send_signal(signal)
                sent_signals[symbol] = time.time()
                log(f"✅ Signal sent: {symbol} ({signal['confidence']}%)")

            except Exception as e:
                log(f"❌ Error for {symbol}: {e}")

        update_signal_status()
        time.sleep(120)

def run_analysis_once():
    exchange = ccxt.binance()
    symbols = [s for s in exchange.load_markets() if "/USDT" in s]
    for symbol in symbols[:20]:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
            signal = calculate_indicators(symbol, ohlcv)
            if not signal:
                continue
            signal['prediction'] = predict_trend(symbol, ohlcv)
            log_signal_to_csv(signal)
            send_signal(signal)
        except Exception as e:
            log(f"❌ Manual Scan Error: {symbol} -> {e}")
