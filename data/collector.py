from binance.client import Client
import pandas as pd

binance_client = Client(api_key='your_api_key', api_secret='your_api_secret')

def collect_data(symbol):
    klines = binance_client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
    data = pd.DataFrame(klines, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume', 'close_time', 'quote_asset_vol', 'number_of_trades', 'taker_buy_base_asset_vol', 'taker_buy_quote_asset_vol', 'ignore'])
    data['timestamp'] = pd.to_datetime(data['timestamp'], unit='ms')
    return data
