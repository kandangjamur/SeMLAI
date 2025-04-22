import time
import ccxt
from core.indicators import calculate_indicators
from core.multi_timeframe import multi_timeframe_boost
from model.predictor import predict_trend
from telebot.bot import send_signal
from utils.logger import log, log_signal_to_csv
from data.tracker import update_signal_status

blacklist = ["BULL", "BEAR", "2X", "3X", "5X", "DOWN", "UP", "ETF"]
sent_signals = {}

def is_blacklisted(symbol):
    return any(term in symbol for term in blacklist)

def log_debug_info(signal):
    log(f"📌 AUDIT LOG — {signal['symbol']}")
    log(f"Confidence: {signal['confidence']}% | Type: {signal['trade_type']}")
    log(f"TP1: {signal['tp1']} | TP2: {signal['tp2']} | TP3: {signal['tp3']} | SL: {signal['sl']}")
    log(f"Support: {signal.get('support')} | Resistance: {signal.get('resistance')}")
    log(f"Leverage: {signal['leverage']}x | Prediction: {signal['prediction']}")

def run_analysis_loop():
    log("📊 Starting Market Scan")
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    symbols = [s for s in markets if "/USDT" in s and not is_blacklisted(s)]

    while True:
        log("🔁 New Scan Cycle")
        for symbol in symbols:
            log(f"🔍 Scanning: {symbol}")
            try:
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                if not ohlcv or len(ohlcv) < 50:
                    continue

                ticker = exchange.fetch_ticker(symbol)
                if ticker.get("baseVolume", 0) < 100000:
                    log(f"⚠️ Skipped {symbol} - Low volume")
                    continue

                signal = calculate_indicators(symbol, ohlcv)
                if not signal:
                    continue

                log(f"🧠 Base Confidence: {signal['confidence']}% | Type: {signal['trade_type']}")

                if signal["tp2"] - signal["price"] < 0.015:
                    log(f"⚠️ Skipped {symbol} - Weak TP2 margin")
                    continue

                support = signal.get("support")
                resistance = signal.get("resistance")
                price = signal["price"]
                atr = signal.get("atr", 0)
                buffer = atr * 1.5 if atr else price * 0.01

                direction = predict_trend(symbol, ohlcv)
                signal["prediction"] = direction

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

                mtf_boost = multi_timeframe_boost(symbol, exchange, direction)
                signal["confidence"] += mtf_boost
                if mtf_boost:
                    log(f"📊 Multi-timeframe Boost: +{mtf_boost}%")

                log(f"🧠 Final Confidence: {signal['confidence']}%")

                if symbol in sent_signals and time.time() - sent_signals[symbol] < 1800:
                    continue

                log_debug_info(signal)
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
    symbols = [s for s in exchange.load_markets() if "/USDT" in s and not is_blacklisted(s)]
    for symbol in symbols[:20]:
        try:
            ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
            if not ohlcv:
                continue
            signal = calculate_indicators(symbol, ohlcv)
            if not signal:
                continue
            signal["prediction"] = predict_trend(symbol, ohlcv)
            log_debug_info(signal)
            log_signal_to_csv(signal)
            send_signal(signal)
        except Exception as e:
            log(f"❌ Manual Scan Error: {symbol} -> {e}")
