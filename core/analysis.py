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
    log(f"TP1: {signal['tp1']} ({signal['tp1_possibility']}%) | TP2: {signal['tp2']} ({signal['tp2_possibility']}%) | TP3: {signal['tp3']} ({signal['tp3_possibility']}%) | SL: {signal['sl']}")
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
            try:
                log(f"🔍 Scanning: {symbol}")
                ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                if not ohlcv or len(ohlcv) < 50:
                    continue

                ticker = exchange.fetch_ticker(symbol)
                if ticker.get("baseVolume", 0) < 120000:
                    continue

                signal = calculate_indicators(symbol, ohlcv)
                if not signal:
                    continue

                price = signal["price"]
                log(f"🧠 Base Confidence: {signal['confidence']}% | Type: {signal['trade_type']}")

                if signal["tp2"] - price < 0.01:
                    continue

                support = signal.get("support")
                resistance = signal.get("resistance")
                atr = signal.get("atr", 0)
                buffer = atr * 1.5 if atr else price * 0.01

                direction = predict_trend(symbol, ohlcv)
                signal["prediction"] = direction

                if direction == "LONG":
                    if resistance and resistance - price > buffer:
                        signal["confidence"] += 5
                    else:
                        continue
                elif direction == "SHORT":
                    if support and price - support > buffer:
                        signal["confidence"] += 5
                    else:
                        continue
                else:
                    continue

                mtf_boost = multi_timeframe_boost(symbol, exchange, direction)
                signal["confidence"] += mtf_boost

                # 🎯 Add dynamic TP possibilities
                signal["tp1_possibility"] = round(max(50, 100 - abs(signal["tp1"] - price) / price * 100), 2)
                signal["tp2_possibility"] = round(max(40, 95 - abs(signal["tp2"] - price) / price * 100), 2)
                signal["tp3_possibility"] = round(max(30, 90 - abs(signal["tp3"] - price) / price * 100), 2)

                log(f"🧠 Final Confidence: {signal['confidence']}%")

                if symbol in sent_signals and time.time() - sent_signals[symbol] < 900:
                    continue

                log_debug_info(signal)
                log_signal_to_csv(signal)
                send_signal(signal)
                sent_signals[symbol] = time.time()

            except Exception as e:
                log(f"❌ Error for {symbol}: {e}")

        update_signal_status()
        time.sleep(120)
