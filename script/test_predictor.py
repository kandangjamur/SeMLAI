import logging
from model.predictor import SignalPredictor
import os
import sys
import asyncio
import pandas as pd
import ccxt
import random
from datetime import datetime

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
log = logging.getLogger("crypto-signal-bot")


async def test_predictor():
    """Test the SignalPredictor with real data"""
    log.info("Testing SignalPredictor with real data")

    predictor = SignalPredictor()
    log.info("Initialized SignalPredictor")

    # Create exchange
    exchange = ccxt.binance({
        'enableRateLimit': True
    })

    # Load top 10 symbols by volume
    markets = exchange.load_markets()
    usdt_symbols = [s for s in exchange.symbols if s.endswith('/USDT')]
    random.shuffle(usdt_symbols)  # Randomize
    test_symbols = usdt_symbols[:5]  # Test 5 random symbols

    for symbol in test_symbols:
        log.info(f"Testing predictor with {symbol}")

        for timeframe in ['15m', '1h', '4h', '1d']:
            try:
                # Fetch OHLCV data
                ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=100)

                # Convert to DataFrame
                df = pd.DataFrame(
                    ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
                df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                df.set_index('timestamp', inplace=True)

                log.info(f"Fetched {len(df)} candles for {symbol} {timeframe}")

                # Calculate indicators
                df_with_indicators = await predictor.calculate_indicators(df)

                # Check if indicators were calculated correctly
                required_indicators = [
                    'rsi', 'macd', 'macdsignal', 'upper_band', 'lower_band', 'atr']
                missing = [
                    ind for ind in required_indicators if ind not in df_with_indicators.columns]

                if missing:
                    log.warning(f"Missing indicators: {missing}")
                else:
                    log.info(f"All indicators calculated successfully")

                # Generate signal
                signal = await predictor.predict_signal(symbol, df_with_indicators, timeframe)

                if signal:
                    log.info(
                        f"Signal generated for {symbol} {timeframe}: {signal['direction']} with {signal['confidence']:.2f}% confidence")

                    # Check all required fields are present
                    required_fields = ['symbol', 'direction', 'confidence',
                                       'entry', 'tp1', 'tp2', 'tp3', 'sl', 'timestamp', 'timeframe']
                    missing_fields = [
                        f for f in required_fields if f not in signal]

                    if missing_fields:
                        log.warning(
                            f"Missing fields in signal: {missing_fields}")
                    else:
                        log.info("Signal contains all required fields")
                else:
                    log.info(f"No signal generated for {symbol} {timeframe}")

            except Exception as e:
                log.error(f"Error testing {symbol} {timeframe}: {str(e)}")

            await asyncio.sleep(1)  # Rate limit

    log.info("Predictor test completed")

if __name__ == "__main__":
    asyncio.run(test_predictor())
