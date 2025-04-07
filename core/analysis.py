from core.indicators import calculate_rsi, calculate_macd, calculate_ema
from core.trade_classifier import classify_trade_type
from core.whale_detector import check_whale_activity
from core.news_sentiment import fetch_news_impact
from binance.client import Client

binance_client = Client(api_key='your_api_key', api_secret='your_api_secret')

def generate_signals():
    # Fetch all USDT pairs
    all_symbols = [s['symbol'] for s in binance_client.get_exchange_info()['symbols'] if 'USDT' in s['symbol']]
    signals = []
    for symbol in all_symbols:
        # Perform analysis for each symbol
        rsi = calculate_rsi(symbol)
        macd = calculate_macd(symbol)
        ema = calculate_ema(symbol)
        whale_activity = check_whale_activity(symbol)
        news_impact = fetch_news_impact(symbol)

        # Combine all the indicators for final signal
        trade_type = classify_trade_type(rsi, macd, ema, whale_activity, news_impact)
        signal = {
            'symbol': symbol,
            'rsi': rsi,
            'macd': macd,
            'ema': ema,
            'whale_activity': whale_activity,
            'news_impact': news_impact,
            'trade_type': trade_type
        }
        signals.append(signal)
    return signals
