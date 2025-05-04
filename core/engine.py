import numpy as np
from utils.logger import log
import ta
import pandas as pd

async def predict_trend(symbol, exchange):
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe="15m", limit=50)
        if len(ohlcv) < 20:
            log(f"Insufficient data for trend prediction for {symbol}")
            return None

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        closes = df["close"].values

        ema12 = ta.trend.EMAIndicator(df["close"], window=12, fillna=True).ema_indicator()
        ema26 = ta.trend.EMAIndicator(df["close"], window=26, fillna=True).ema_indicator()
        ema_cross_long = ema12.iloc[-1] > ema26.iloc[-1] and ema12.iloc[-2] <= ema26.iloc[-2]
        ema_cross_short = ema12.iloc[-1] < ema26.iloc[-1] and ema12.iloc[-2] >= ema26.iloc[-2]

        adx = ta.trend.ADXIndicator(df["high"], df["low"], df["close"], window=14, fillna=True).adx()
        trend_strength = adx.iloc[-1] > 25

        rsi = ta.momentum.RSIIndicator(df["close"], window=14, fillna=True).rsi()
        rsi_overbought = rsi.iloc[-1] > 70
        rsi_oversold = rsi.iloc[-1] < 30

        stoch_rsi = ta.momentum.StochRSIIndicator(df["close"], fillna=True).stochrsi_k()
        stoch_overbought = stoch_rsi.iloc[-1] > 0.8
        stoch_oversold = stoch_rsi.iloc[-1] < 0.2

        three_candle_long = closes[-1] > closes[-2] > closes[-3]
        three_candle_short = closes[-1] < closes[-2] < closes[-3]

        confidence_long = 0
        confidence_short = 0
        if ema_cross_long:
            confidence_long += 30
        if trend_strength:
            confidence_long += 20
            confidence_short += 20
        if rsi_oversold:
            confidence_long += 20
        if stoch_oversold:
            confidence_long += 15
        if three_candle_long:
            confidence_long += 15
        if ema_cross_short:
            confidence_short += 30
        if rsi_overbought:
            confidence_short += 20
        if stoch_overbought:
            confidence_short += 15
        if three_candle_short:
            confidence_short += 15

        if confidence_long >= 85 and confidence_long > confidence_short:
            log(f"LONG trend detected for {symbol}")
            return "LONG"
        elif confidence_short >= 85 and confidence_short > confidence_long:
            log(f"SHORT trend detected for {symbol}")
            return "SHORT"

        return None
    except Exception as e:
        log(f"Error predicting trend for {symbol}: {e}", level='ERROR')
        return None
