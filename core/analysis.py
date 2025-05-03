from core.indicators import calculate_indicators
from utils.logger import setup_logger

logger = setup_logger("Analysis")

async def analyze_market(exchange, symbols, confidence_threshold):
    for symbol in symbols:
        try:
            ohlcv = await exchange.fetch_ohlcv(symbol, timeframe="15m", limit=100)
            if not ohlcv or len(ohlcv) < 50:
                continue

            indicators = calculate_indicators(ohlcv)
            if indicators and indicators.get("confidence", 0) >= confidence_threshold:
                logger.info(f"{symbol} signal: {indicators['direction']} | Confidence: {indicators['confidence']}")
        except Exception as e:
            logger.warning(f"Skipping {symbol} due to error: {e}")
