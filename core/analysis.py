import pandas as pd
import numpy as np
import os
from binance.client import Client
import ta
from utils.logger import log

# Initialize Binance client (replace with actual keys in production or use env vars)
binance_client = Client(
    api_key=os.getenv('BINANCE_API_KEY'),
    api_secret=os.getenv('BINANCE_API_SECRET')
)

# Timeframes to scan
TIMEFRAMES = {
    '15m': Client.KLINE_INTERVAL_15MINUTE,
    '30m': Client.KLINE_INTERVAL_30MINUTE,
    '1h': Client.KLINE_INTERVAL_1HOUR,
    '4h': Client.KLINE_INTERVAL_4HOUR
}

# Fetch OHLCV data for given symbol & timeframe
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

# Calculate technical indicators
def calculate_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
    df['macd'] = ta.trend.MACD(df['close']).macd()
    df['macd_signal'] = ta.trend.MACD(df['close']).macd_signal()
    df['ema_12'] = ta.trend.EMAIndicator(df['close'], window=12).ema_indicator()
    df['ema_26'] = ta.trend.EMAIndicator(df['close'], window=26).ema_indicator()
    df['bb_lower'], df['bb_middle'], df['bb_upper'] = ta.volatility.BollingerBands(df['close']).bollinger_lband(), ta.volatility.BollingerBands(df['close']).bollinger_mavg(), ta.volatility.BollingerBands(df['close']).bollinger_hband()
    df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
    df['volume_change'] = df['volume'].pct_change() * 100  # Percentage change in volume

    return df

# Score signal based on multiple hedge-fund level indicators
def score_signal(indicators):
    score = 0
    conditions = []

    # RSI condition
    if indicators['rsi'].iloc[-1] < 30:
        score += 1
        conditions.append('RSI oversold')

    # MACD crossover
    if indicators['macd'].iloc[-1] > indicators['macd_signal'].iloc[-1]:
        score += 1
        conditions.append('MACD bullish crossover')

    # EMA crossover
    if indicators['ema_12'].iloc[-1] > indicators['ema_26'].iloc[-1]:
        score += 1
        conditions.append('EMA 12 > EMA 26')

    # Volume spike (100%+ change)
    if indicators['volume_change'].iloc[-1] > 50:
        score += 1
        conditions.append('Volume spike detected')

    # Bollinger Band lower touch (buy signal)
    if indicators['close'].iloc[-1] < indicators['bb_lower'].iloc[-1]:
        score += 1
        conditions.append('Bollinger lower band touch')

    # ATR rising = increasing volatility
    if indicators['atr'].iloc[-1] > indicators['atr'].iloc[-2]:
        score += 1
        conditions.append('ATR rising')

    confidence = round((score / 6) * 100, 2)
    return score, confidence, conditions

# Analyze single symbol across timeframes
def analyze_symbol(symbol):
    try:
        final_signals = []

        for tf_label, interval in TIMEFRAMES.items():
            df = fetch_ohlcv(symbol, interval)
            if df is None or len(df) < 20:
                continue

            indicators = calculate_indicators(df)
            score, confidence, reasons = score_signal(indicators)

            if score >= 4:  # Triple verification threshold
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

# Analyze all symbols (only USDT pairs)
def analyze_all_symbols(symbols):
    all_signals = []
    for symbol in symbols:
        if not symbol.endswith('USDT'):
            continue
        result = analyze_symbol(symbol)
        if result:
            all_signals.extend(result)
    return all_signals

# Log function for general use
def log(message):
    print(f"[LOG] {message}")
