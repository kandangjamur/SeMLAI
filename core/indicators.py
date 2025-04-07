import talib
import numpy as np
from binance.client import Client

binance_client = Client(api_key='your_api_key', api_secret='your_api_secret')

def calculate_rsi(symbol):
    # Fetch historical data
    klines = binance_client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
    closes = [float(kline[4]) for kline in klines]
    return talib.RSI(np.array(closes), timeperiod=14)[-1]

def calculate_macd(symbol):
    klines = binance_client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
    closes = [float(kline[4]) for kline in klines]
    macd, signal, hist = talib.MACD(np.array(closes), fastperiod=12, slowperiod=26, signalperiod=9)
    return macd[-1], signal[-1], hist[-1]

def calculate_ema(symbol):
    klines = binance_client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
    closes = [float(kline[4]) for kline in klines]
    return talib.EMA(np.array(closes), timeperiod=9)[-1]
