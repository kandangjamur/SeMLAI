import pandas as pd
from binance.client import Client
from core.indicators import calculate_indicators
from core.analysis import score_signal
from utils.logger import log

binance_client = Client(api_key='your_api_key', api_secret='your_api_secret')

TIMEFRAMES = {
    '15m': Client.KLINE_INTERVAL_15MINUTE,
    '30m': Client.KLINE_INTERVAL_30MINUTE,
    '1h': Client.KLINE_INTERVAL_1HOUR,
    '4h': Client.KLINE_INTERVAL_4HOUR
}

def fetch_ohlcv(symbol, interval, lookback='500'):
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

def backtest_strategy(symbol):
    results = []
    
    for tf_label, interval in TIMEFRAMES.items():
        df = fetch_ohlcv(symbol, interval)
        if df is None or len(df) < 50:
            continue

        for i in range(50, len(df)):
            window = df.iloc[:i]
            indicators = calculate_indicators(window)
            score, confidence, reasons = score_signal(indicators)

            if score >= 4:
                results.append({
                    'symbol': symbol,
                    'timeframe': tf_label,
                    'index': i,
                    'score': score,
                    'confidence': confidence,
                    'price': window['close'].iloc[-1],
                    'reasons': reasons
                })

    return results

def run_backtest(symbols):
    full_results = []
    for symbol in symbols:
        if not symbol.endswith('USDT'):
            continue
        try:
            symbol_results = backtest_strategy(symbol)
            full_results.extend(symbol_results)
        except Exception as e:
            log(f"Backtest error for {symbol}: {e}")
    return full_results
