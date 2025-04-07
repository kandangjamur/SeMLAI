import time
from binance.client import Client
from core.analysis import analyze_market
from core.indicators import calculate_indicators
from core.news_sentiment import fetch_news_impact
from core.whale_detector import check_whale_activity
from core.trade_classifier import classify_trade
from datetime import datetime
import random

class CryptoScanner:
    def __init__(self, binance_api_key, binance_api_secret):
        # Initialize Binance Client
        self.client = Client(binance_api_key, binance_api_secret)
        self.symbols = [s['symbol'] for s in self.client.get_exchange_info()['symbols'] if 'USDT' in s['symbol']]  # USDT pairs only

    def scan_market(self, timeframe='1h'):
        """
        Scans the market for all pairs at the given timeframe and checks if any signals are triggered.
        """
        signals = []

        for symbol in self.symbols:
            try:
                # Fetch the historical data
                klines = self.client.get_klines(symbol=symbol, interval=timeframe, limit=100)
                close_price = float(klines[-1][4])  # Close price of the most recent candle

                # Perform analysis
                indicators = calculate_indicators(symbol, timeframe, klines)
                news_impact = fetch_news_impact(symbol)
                whale_activity = check_whale_activity(symbol)
                trade_type = classify_trade(indicators)

                # Analyze market and generate signal if conditions are met
                signal = analyze_market(symbol, indicators, news_impact, whale_activity, close_price, trade_type)
                if signal:
                    signals.append(signal)

            except Exception as e:
                print(f"Error scanning {symbol}: {e}")

        return signals

    def print_signals(self, signals):
        """
        Print out the signals for the user or send them to a Telegram bot.
        """
        if not signals:
            print(f"[{datetime.now()}] No signals triggered.")
        else:
            for signal in signals:
                print(f"[{datetime.now()}] Signal for {signal['symbol']}: {signal['trade_type']} - {signal['confidence']} - TP1: {signal['tp1']} TP2: {signal['tp2']} SL: {signal['sl']}")

    def start_scanning(self, timeframe='1h', interval=3600):
        """
        Continuously scan the market at the specified timeframe and interval (in seconds).
        """
        print(f"Starting market scan every {interval} seconds...")
        while True:
            print(f"Scanning the market for {timeframe} timeframe...")
            signals = self.scan_market(timeframe)
            self.print_signals(signals)
            time.sleep(interval)

if __name__ == "__main__":
    # Example: Set your Binance API keys here
    binance_api_key = "HHjRMBH35MWjSg6Y7Oe4w9ehai8fYGsG3qqsH4mbgU5S0D7VO7YPYdwPHekIxq7q"
    binance_api_secret = "A5QA8xMR5b54ngMq9C5jK6KTmpf6UcWqpwpNYvvaa3nO6YlDBr4M0K16QlU43c0L"

    scanner = CryptoScanner(binance_api_key, binance_api_secret)
    scanner.start_scanning(timeframe='1h', interval=3600)  # Scanning every 1 hour
