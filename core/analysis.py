import pandas as pd
import numpy as np
from binance.client import Client
from core.indicators import calculate_indicators
from utils.logger import log

binance_client = Client(api_key='your_api_key', api_secret='your_api_secret')

TIMEFRAMES = {
    '15m': Client.KLINE_INTERVAL_15MINUTE,
    '30m': Client.KLINE_INTERVAL_30MINUTE,
    '1h': Client.KLINE_INTERVAL_1HOUR,
    '4h': Client.KLINE_INTERVAL_4HOUR
}

def fetch_ohlcv(symbol, interval, lookback='100'):
    try:
        klines = binance_client.get_klines(symbol=symbol, interval=interval, limit=int(lookback))
        df = pd.DataFrame(klines, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_volume', 'taker_buy_quote_volume', 'ignore'
        ])
        df['close'] = pd.to_numeric(df['close'])
        df['high'] = pd.to_numeric(df['high'])
        df['low'] = pd.to_numeric(df['low'])
        df['open'] = pd.to_numeric(df['open'])
        df['volume'] = pd.to_numeric(df['volume'])
        return df
    except Exception as e:
        log(f"Error fetching OHLCV for {symbol}: {e}")
        return None

def score_signal(indicators):
    score = 0
    conditions = []

    # Example scoring conditions (you can add more based on strategy)
    if indicators['rsi'] < 30:
        score += 1
        conditions.append('RSI oversold')
    if indicators['macd'] > indicators['macd_signal']:
        score += 1
        conditions.append('MACD crossover')
    if indicators['ema_fast'] > indicators['ema_slow']:
        score += 1
        conditions.append('EMA crossover')
    if indicators['volume_spike']:
        score += 1
        conditions.append('Volume spike')
    if indicators['bollinger_signal'] == 'buy':
        score += 1
        conditions.append('Bollinger signal')
    if indicators['atr_rising']:
        score += 1
        conditions.append('ATR rising')

    confidence = round((score / 6) * 100, 2)
    return score, confidence, conditions

def analyze_symbol(symbol):
    try:
        final_signals = []

        for tf_label, interval in TIMEFRAMES.items():
            df = fetch_ohlcv(symbol, interval)
            if df is None or len(df) < 20:
                continue

            indicators = calculate_indicators(df)
            score, confidence, reasons = score_signal(indicators)

            if score >= 4:  # Triple verification
                final_signals.append({
                    'symbol': symbol,
                    'timeframe': tf_label,
                    'score': score,
                    'confidence': confidence,
                    'reasons': reasons,
                    'price': df['close'].iloc[-1]
                })

        return final_signals

    except Exception as e:
        log(f"Error in analyze_symbol for {symbol}: {e}")
        return []

def analyze_all_symbols(symbols):
    all_signals = []
    for symbol in symbols:
        if not symbol.endswith('USDT'):
            continue
        result = analyze_symbol(symbol)
        if result:
            all_signals.extend(result)
    return all_signals
