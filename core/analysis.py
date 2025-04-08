# core/analysis.py

import pandas as pd
from binance.client import Client
from core.indicators import calculate_indicators
from utils.logger import log
import numpy as np

client = Client()

TIMEFRAMES = {
    '15m': Client.KLINE_INTERVAL_15MINUTE,
    '30m': Client.KLINE_INTERVAL_30MINUTE,
    '1h': Client.KLINE_INTERVAL_1HOUR,
    '4h': Client.KLINE_INTERVAL_4HOUR,
}

def fetch_ohlcv(symbol, interval, limit=200):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=limit)
    df = pd.DataFrame(klines, columns=[
        'timestamp', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'num_trades',
        'taker_buy_base_asset_volume', 'taker_buy_quote_asset_volume', 'ignore'
    ])
    df['close'] = df['close'].astype(float)
    df['volume'] = df['volume'].astype(float)
    return df

def score_signal(indicators):
    score = 0
    reasons = []

    if indicators['rsi'] < 30:
        score += 1
        reasons.append("RSI Oversold")

    if indicators['macd_hist'] > 0 and indicators['macd'] > indicators['signal']:
        score += 1
        reasons.append("MACD Bullish")

    if indicators['ema_9'] > indicators['ema_21']:
        score += 1
        reasons.append("EMA Crossover Bullish")

    if indicators['volume_spike']:
        score += 1
        reasons.append("Volume Spike")

    if indicators['price_above_bbands']:
        score += 1
        reasons.append("Price Above Upper Bollinger Band")

    if indicators['atr'] > indicators['atr_mean']:
        score += 1
        reasons.append("ATR Volatility High")

    confidence = (score / 6) * 100
    return score, confidence, reasons

def analyze_symbol(symbol):
    results = []

    for tf_name, tf_interval in TIMEFRAMES.items():
        df = fetch_ohlcv(symbol, tf_interval)
        if df.empty or len(df) < 50:
            continue

        indicators = calculate_indicators(df)
        score, confidence, reasons = score_signal(indicators)

        if confidence >= 90:  # High-confidence signal threshold
            results.append({
                'symbol': symbol,
                'timeframe': tf_name,
                'confidence': confidence,
                'score': score,
                'reasons': reasons,
                'close': df['close'].iloc[-1]
            })

    return results

def scan_market():
    all_symbols = [s['symbol'] for s in client.get_ticker_price() if s['symbol'].endswith('USDT')]
    verified_signals = []

    for symbol in all_symbols:
        try:
            symbol_results = analyze_symbol(symbol)
            verified_signals.extend(symbol_results)
        except Exception as e:
            log(f"Error analyzing {symbol}: {e}")

    return verified_signals
