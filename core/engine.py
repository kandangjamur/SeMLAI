import numpy as np
from utils.logger import log
import ta
import pandas as pd

async def predict_trend(symbol, exchange):
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe="15m", limit=50)
        if len(ohlcv) < 20:
            log(f"⚠️ Insufficient data for trend prediction for {symbol}")
            return None

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        closes = df["close"].values
        highs = df["high"].values
        lows = df["low"].values

        ema12 = ta.trend.EMAIndicator(df["close"], window=12, fillna=True).ema_indicator()
        ema26 = ta.trend.EMAIndicator(df["close"], window=26, fillna=True).ema_indicator()
        ema_cross_long = ema12.iloc[-1] > ema26.iloc[-1] and ema12.iloc[-2] <= ema26.iloc[-2]
        ema_cross_short = ema12.iloc[-1] < ema26.iloc[-1] and ema12.iloc[-2] >= ema26.iloc[-2]

        adx = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=14, fillna=True).adx()
        trend_strength = adx.iloc[-1] > 25

        order_book = await exchange.fetch_order_book(symbol, limit=10)
        buy_pressure = sum([x[1] for x in order_book['bids']])
        sell_pressure = sum([x[1] for x in order_book['asks']])
        sentiment_long = buy_pressure > sell_pressure * 1.2
        sentiment_short = sell_pressure > buy_pressure * 1.2

        atr = ta.volatility.AverageTrueRange(df["high"], df["low"], df["close"], fillna=True).average_true_range()
        if atr.iloc[-1] < atr[-10:].mean() * 0.5:
            log(f"⚠️ Low volatility for {symbol}, no trend")
            return None

        three_candle_long = closes[-1] > closes[-2] > closes[-3]
        three_candle_short = closes[-1] < closes[-2] < closes[-3]

        if ema_cross_long and trend_strength and sentiment_long and three_candle_long:
            log(f"✅ LONG trend detected for {symbol}")
            return "LONG"
        elif ema_cross_short and trend_strength and sentiment_short and three_candle_short:
            log(f"✅ SHORT trend detected for {symbol}")
            return "SHORT"

        log(f"⚠️ No clear trend for {symbol}")
        return None
    except Exception as e:
        log(f"❌ Error predicting trend for {symbol}: {e}")
        return None
