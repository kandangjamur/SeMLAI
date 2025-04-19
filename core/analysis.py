import time, ccxt
from core.indicators import calculate_indicators
from model.predictor import predict_trend
from telebot.bot import send_signal
from utils.logger import log, log_signal_to_csv
from core.news_sentiment import get_sentiment_boost
from core.whale_detector import whale_check

sent_signals = {}

def run_analysis_loop():
    log("📊 Starting Market Scan")
    exchange = ccxt.binance()
    markets = exchange.load_markets()
    symbols = [s for s in markets if "/USDT" in s and not s.endswith("UP/USDT") and not s.endswith("DOWN/USDT")]
    log(f"🔢 Total USDT Pairs Loaded: {len(symbols)}")

    while True:
        try:
            log("🔁 New Scan Cycle")
            for symbol in symbols:
                log(f"🔍 Scanning: {symbol}")
                try:
                    ohlcv = exchange.fetch_ohlcv(symbol, '15m', limit=100)
                    signal = calculate_indicators(symbol, ohlcv)
                except:
                    continue
                if not signal:
                    continue

                signal['confidence'] += get_sentiment_boost(symbol)
                if signal['trade_type'] == "Scalping" and signal['confidence'] < 60:
                    continue
                if signal['trade_type'] == "Normal" and signal['confidence'] < 75:
                    continue
                if symbol in sent_signals and time.time() - sent_signals[symbol] < 1800:
                    continue
                if not whale_check(symbol, exchange):
                    continue

                signal['prediction'] = predict_trend(symbol, ohlcv)
                price = signal["price"]
                atr = signal.get("atr", 0)

                if signal["prediction"] == "LONG":
                    signal["tp1"] = round(price + atr * 1.2, 3)
                    signal["tp2"] = round(price + atr * 2, 3)
                    signal["tp3"] = round(price + atr * 3, 3)
                    signal["sl"] = round(price - atr * 1.2, 3)
                else:
                    signal["tp1"] = round(price - atr * 1.2, 3)
                    signal["tp2"] = round(price - atr * 2, 3)
                    signal["tp3"] = round(price - atr * 3, 3)
                    signal["sl"] = round(price + atr * 1.2, 3)

                signal["trailing_sl"] = round(atr * 0.75, 3)
                sent_signals[symbol] = time.time()
                log_signal_to_csv(signal)
                send_signal(signal)
        except Exception as e:
            log(f"❌ Analysis Error: {e}")
        time.sleep(120)
