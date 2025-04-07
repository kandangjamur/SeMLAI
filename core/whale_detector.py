from binance.client import Client

binance_client = Client(api_key='your_api_key', api_secret='your_api_secret')

def check_whale_activity(symbol):
    # Example of checking whale activity (large volume trades)
    klines = binance_client.get_historical_klines(symbol, Client.KLINE_INTERVAL_1MINUTE, "1 day ago UTC")
    volumes = [float(kline[5]) for kline in klines]
    average_volume = sum(volumes) / len(volumes)
    return max(volumes) > (average_volume * 2)  # Adjust factor as needed
