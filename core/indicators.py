import pandas as pd
import ta
import ccxt

exchange = ccxt.binance()

def fetch_ohlcv_tf(symbol, timeframe='15m', limit=100):
    try:
        return exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    except:
        return None

def calculate_indicators(symbol, ohlcv_15m):
    if len(ohlcv_15m) < 50:
        return None

    df_15 = pd.DataFrame(ohlcv_15m, columns=["timestamp", "open", "high", "low", "close", "volume"])
    df_15["ema_20"] = ta.trend.EMAIndicator(df_15["close"], window=20).ema_indicator()
    df_15["ema_50"] = ta.trend.EMAIndicator(df_15["close"], window=50).ema_indicator()
    df_15["rsi"] = ta.momentum.RSIIndicator(df_15["close"], window=14).rsi()
    macd = ta.trend.MACD(df_15["close"])
    df_15["macd"] = macd.macd()
    df_15["macd_signal"] = macd.macd_signal()
    df_15["atr"] = ta.volatility.AverageTrueRange(df_15["high"], df_15["low"], df_15["close"]).average_true_range()
    df_15["volume_sma"] = df_15["volume"].rolling(window=20).mean()

    latest = df_15.iloc[-1]
    confidence = 0

    # ✅ Base Indicators Scoring
    if latest["ema_20"] > latest["ema_50"]: confidence += 20
    if latest["rsi"] > 55: confidence += 15
    if latest["macd"] > latest["macd_signal"]: confidence += 15
    if latest["volume"] > 1.5 * latest["volume_sma"]: confidence += 20
    if latest["atr"] > 0: confidence += 10

    # ✅ Add Multi-timeframe Boost
    tf_match = 0
    for tf in ['1h', '4h']:
        ohlcv_tf = fetch_ohlcv_tf(symbol, tf)
        if ohlcv_tf and len(ohlcv_tf) >= 50:
            df_tf = pd.DataFrame(ohlcv_tf, columns=["timestamp", "open", "high", "low", "close", "volume"])
            ema_tf = ta.trend.EMAIndicator(df_tf["close"], window=20).ema_indicator()
            ema_tf_50 = ta.trend.EMAIndicator(df_tf["close"], window=50).ema_indicator()
            if ema_tf.iloc[-1] > ema_tf_50.iloc[-1]:
                tf_match += 1

    confidence += tf_match * 10  # +10 for each timeframe alignment

    # ✅ Dynamic Trade Type Classification
    trade_type = "Scalping"
    if confidence >= 90:
        trade_type = "Normal"
    elif confidence >= 80:
        trade_type = "Scalping"
    else:
        return None  # skip low-confidence

    price = latest["close"]
    atr = latest["atr"]

    # ✅ Improved TP/SL by volatility
    tp1 = round(price + atr * 2, 3)
    tp2 = round(price + atr * 4, 3)
    tp3 = round(price + atr * 6, 3)
    sl = round(price - atr * 1.5, 3)

    leverage = min(max(int(confidence / 2), 3), 50)

    return {
        "symbol": symbol,
        "price": price,
        "confidence": round(confidence, 2),
        "trade_type": trade_type,
        "timestamp": latest["timestamp"],
        "tp1": tp1,
        "tp2": tp2,
        "tp3": tp3,
        "sl": sl,
        "atr": atr,
        "leverage": leverage
    }
