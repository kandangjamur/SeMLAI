import pandas as pd
import numpy as np
import os
from binance.client import Client
import ta

# Initialize Binance client
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

# Fetch OHLCV data
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
        print(f"[ERROR] OHLCV fetch failed for {symbol}: {e}")
        return None

# Calculate indicators
def calculate_indicators(df):
    df['rsi'] = ta.momentum.RSIIndicator(df['close']).rsi()
    macd = ta.trend.MACD(df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['ema_12'] = ta.trend.EMAIndicator(df['close'], window=12).ema_indicator()
    df['ema_26'] = ta.trend.EMAIndicator(df['close'], window=26).ema_indicator()
    bb = ta.volatility.BollingerBands(df['close'])
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_upper'] = bb.bollinger_hband()
    df['close'] = pd.to_numeric(df['close'])
    df['atr'] = ta.volatility.AverageTrueRange(df['high'], df['low'], df['close']).average_true_range()
    df['volume_change'] = df['volume'].pct_change() * 100
    return df

# Score signal logic
def score_signal(indicators):
    score = 0
    conditions = []

    if indicators['rsi'].iloc[-1] < 30:
        score += 1
        conditions.append('RSI oversold')

    if indicators['macd'].iloc[-1] > indicators['macd_signal'].iloc[-1]:
        score += 1
        conditions.append('MACD bullish crossover')

    if indicators['ema_12'].iloc[-1] > indicators['ema_26'].iloc[-1]:
        score += 1
        conditions.append('EMA 12 > EMA 26')

    if indicators['volume_change'].iloc[-1] > 50:
        score += 1
        conditions.append('Volume spike')

    if indicators['close'].iloc[-1] < indicators['bb_lower'].iloc[-1]:
        score += 1
        conditions.append('Touching Bollinger Lower Band')

    if indicators['atr'].iloc[-1] > indicators['atr'].iloc[-2]:
        score += 1
        conditions.append('ATR rising')

    confidence = round((score / 6) * 100, 2)
    return score, confidence, conditions

# Analyze one symbol
def analyze_symbol(symbol):
    try:
        final_signals = []
        print(f"\n🔍 Analyzing {symbol} for signals...")

        for tf_label, interval in TIMEFRAMES.items():
            df = fetch_ohlcv(symbol, interval)
            if df is None or len(df) < 20:
                print(f"⚠️ Skipping {symbol} {tf_label} — insufficient data")
                continue

            indicators = calculate_indicators(df)
            score, confidence, reasons = score_signal(indicators)

            print(f"[{symbol} - {tf_label}] RSI: {indicators['rsi'].iloc[-1]:.2f}, MACD: {indicators['macd'].iloc[-1]:.4f}, EMA12: {indicators['ema_12'].iloc[-1]:.2f}, Vol Change: {indicators['volume_change'].iloc[-1]:.2f}%")
            print(f"➡️ Signal Score: {score}/6 | Confidence: {confidence}%")

            if score >= 4:
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
        print(f"[ERROR] analyze_symbol failed for {symbol}: {e}")
        return []

# Analyze all symbols (USDT pairs only)
def analyze_all_symbols(symbols):
    all_signals = []
    for symbol in symbols:
        if not symbol.endswith('USDT'):
            continue
        result = analyze_symbol(symbol)
        if result:
            all_signals.extend(result)
    return all_signals
