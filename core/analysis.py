from core.indicators import calculate_indicators
from utils.logger import setup_logger

logger = setup_logger("analysis")

async def analyze_symbol(exchange, symbol):
    try:
        indicators = await calculate_indicators(exchange, symbol)
        if not indicators:
            return None

        signal = indicators.get("signal")
        confidence = indicators.get("confidence")
        tp_possibility = indicators.get("tp_possibility")

        if signal in ["LONG", "SHORT"] and confidence and tp_possibility:
            return {
                "symbol": symbol,
                "signal": signal,
                "confidence": confidence,
                "tp_possibility": tp_possibility,
                "tp1_hit": False
            }

    except Exception as e:
        logger.warning(f"Error analyzing {symbol}: {e}")
    return None
