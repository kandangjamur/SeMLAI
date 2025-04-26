import pandas as pd
import ta
import warnings
import time
import ccxt

from utils.fibonacci import calculate_fibonacci_levels
from utils.support_resistance import detect_sr_levels
from core.candle_patterns import is_bullish_engulfing, is_breakout_candle
from core.multi_timeframe import multi_timeframe_boost
from model.predictor import predict_trend
from utils.logger import log, log_signal_to_csv
from telebot.bot import send_signal
from data.tracker import update_signal_status

warnings.filterwarnings("ignore", category=RuntimeWarning)
sent_signals = {}
blacklist = ["BULL", "BEAR", "2X", "3X", "5X", "DOWN", "UP", "ETF"]

def is_blacklisted(symbol):
    return any(term in symbol for term in blacklist)

def calculate_indicators(symbol, ohlcv):
    if not ohlcv or len(ohlcv) < 50:
        return None

    df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
    if df.isnull().values.any():
        return None

    df["ema_20"] = ta.trend.EMAIndicator(df["close"], window=20).ema_indicator()
    df["ema_50"] = ta.trend.EMAIndicator(df["close"], window=50).ema_indicator()
    df["rsi"] = ta.momentum.RSIIndicator(df["close"], window=14).rsi()
    df["atr"] = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"]).average_true_range()
    macd = ta.trend.MACD(df["close"])
    df["macd"] = macd.macd()
    df["macd_signal"] = macd.macd_signal()
    df["stoch_rsi"] = ta.momentum.StochRSIIndicator(df["close"]).stochrsi_k()
    df["adx"] = ta.trend.ADXIndicator(df["high"], df["low"], df["close"]).adx()
    df["volume_sma"] = df["volume"].rolling(window=20).mean()

    latest = df.iloc[-1].to_dict()
    confidence = 0

    # Scoring
    if latest["ema_20"] > latest["ema_50"]:
        confidence += 20
    if latest["rsi"] > 55 and latest["volume"] > 1.5 * latest["volume_sma"]:
        confidence += 15
    if latest["macd"] > latest["macd_signal"]:
        confidence += 15
    if pd.notna(latest["adx"]) and latest["adx"] > 20:
        confidence += 10
    if latest["stoch_rsi"] < 0.2:
        confidence += 10
    if is_bullish_engulfing(df):
        confidence += 10
    if is_breakout_candle(df):
        confidence += 10

    price = latest["close"]
    atr = latest["atr"]
    sr = detect_sr_levels(df)
    support = sr.get("support")
    resistance = sr.get("resistance")
    midpoint = round((support + resistance) / 2, 3) if support and resistance else None

    fib = calculate_fibonacci_levels(price, direction="LONG")
    tp1 = round(fib.get("tp1", price + atr * 1.2), 3)
    tp2 = round(fib.get("tp2", price + atr * 2.5), 3)
    tp3 = round(fib.get("tp3", price + atr * 4.5), 3)
    sl = round(support if support else price - atr * 1.8, 3)

    tp1_possibility = round(96 - (abs(tp1 - price) / price * 100), 2)
    tp2_possibility = round(87 - (abs(tp2 - price) / price * 100), 2)
    tp3_possibility = round(72 - (abs(tp3 - price) / price * 100), 2)

    if confidence < 75:
        return None

    trade_type = "Normal" if confidence >= 85 else "Scalping"
    leverage = min(max(int(confidence / 2), 3), 50)

    return {
        "symbol": symbol,
        "price": price,
        "confidence": confidence,
        "trade_type": trade_type,
        "timestamp": latest["timestamp"],
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sl": sl,
        "atr": atr,
        "leverage": leverage,
        "support": support,
        "resistance": resistance,
        "midpoint": midpoint,
        "tp1_possibility": tp1_possibility,
        "tp2_possibility": tp2_possibility,
        "tp3_possibility": tp3_possibility,
    }

def log_debug_info(signal):
    log(f"📌 AUDIT LOG — {signal['symbol']}")
    log(f"Confidence: {signal['confidence']}% | Type: {signal['trade_type']}")
    log(f"TP1: {signal['tp1']} | TP2: {signal['tp2']} | TP3: {signal['tp3']} | SL: {signal['sl']}")
    log(f"TP%: {signal['tp1_possibility']} / {signal['tp2_possibility']} / {signal['tp3_possibility']}")
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
                if ticker.get("baseVolume", 0) < 100000:
                    continue

                signal = calculate_indicators(symbol, ohlcv)
                if not signal:
                    continue

                direction = predict_trend(symbol, ohlcv)
                signal["prediction"] = "LONG" if direction == "LONG" else "SHORT"

                if signal["tp2"] - signal["price"] < 0.01:
                    continue

                mtf_boost = multi_timeframe_boost(symbol, exchange, signal["prediction"])
                signal["confidence"] += mtf_boost

                if symbol in sent_signals and time.time() - sent_signals[symbol] < 900:
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
