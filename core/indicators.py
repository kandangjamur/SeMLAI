import ccxt.async_support as ccxt
import numpy as np
import pandas as pd
import ta
from utils.logger import setup_logger

logger = setup_logger("indicators")

exchange = ccxt.binance({'enableRateLimit': True, 'rateLimit': 1200})

async def get_binance_exchange():
    return exchange

async def get_usdt_symbols(exchange):
    try:
        markets = await exchange.load_markets()
        symbols = [s for s in markets if s.endswith("/USDT") and markets[s]["active"]]
        valid = []

        for symbol in symbols:
            try:
                ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='15m', limit=10)
                if ohlcv:
                    valid.append(symbol)
            except Exception:
                continue

        return valid
    except Exception as e:
        logger.error(f"Failed to fetch symbols: {e}")
        return []

def add_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()
    macd = ta.trend.MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['ema50'] = ta.trend.EMAIndicator(close=df['close'], window=50).ema_indicator()
    df['ema200'] = ta.trend.EMAIndicator(close=df['close'], window=200).ema_indicator()
    return df

def evaluate_signal(df):
    latest = df.iloc[-1]
    signal = None
    confidence = 0
    tp_possibility = "LOW"

    if latest['ema50'] > latest['ema200'] and latest['macd'] > latest['macd_signal'] and latest['rsi'] < 70:
        signal = "LONG"
    elif latest['ema50'] < latest['ema200'] and latest['macd'] < latest['macd_signal'] and latest['rsi'] > 30:
        signal = "SHORT"

    if signal:
        confidence += 20 if abs(latest['ema50'] - latest['ema200']) > 0.5 else 10
        confidence += 20 if abs(latest['macd'] - latest['macd_signal']) > 0.5 else 10
        confidence += 10 if 40 < latest['rsi'] < 60 else 5

        if confidence >= 70:
            tp_possibility = "HIGH"
        elif confidence >= 50:
            tp_possibility = "MEDIUM"

    return signal, confidence, tp_possibility

async def calculate_indicators(exchange, symbol):
    try:
        ohlcv = await exchange.fetch_ohlcv(symbol, timeframe='15m', limit=200)
        if not ohlcv:
            return None

        df = pd.DataFrame(ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"])
        df = add_indicators(df)
        signal, confidence, tp_possibility = evaluate_signal(df)

        return {
            "signal": signal,
            "confidence": confidence,
            "tp_possibility": tp_possibility
        }

    except Exception as e:
        logger.warning(f"Indicator calc failed for {symbol}: {e}")
        return None
