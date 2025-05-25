import logging
from telebot.sender import send_telegram_signal
import os
import sys
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
log = logging.getLogger("crypto-signal-bot")


async def test_telegram_signal():
    """Test sending a signal to Telegram with different confidence levels"""
    log.info("Testing Telegram signal sending with different confidence levels")

    # Test signal with 85% confidence (below threshold)
    signal_85 = {
        "symbol": "BTC/USDT",
        "direction": "LONG",
        "confidence": 85.0,
        "entry": 65000.0,
        "sl": 64000.0,
        "tp1": 66000.0,
        "tp2": 67000.0,
        "tp3": 68000.0,
        "tp1_possibility": 0.7,
        "tp2_possibility": 0.5,
        "tp3_possibility": 0.3,
        "timeframe": "1h",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "indicators_used": "RSI, MACD, Volume, BB, S/R"
    }

    # Test signal with 95% confidence (above threshold)
    signal_95 = {
        "symbol": "ETH/USDT",
        "direction": "SHORT",
        "confidence": 95.0,
        "entry": 3500.0,
        "sl": 3550.0,
        "tp1": 3450.0,
        "tp2": 3400.0,
        "tp3": 3350.0,
        "tp1_possibility": 0.7,
        "tp2_possibility": 0.5,
        "tp3_possibility": 0.3,
        "timeframe": "4h",
        "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        "indicators_used": "RSI, MACD, Volume, BB, S/R"
    }

    # Try sending both signals
    log.info("Testing signal with 85% confidence (should be filtered out)...")
    result_85 = await send_telegram_signal("BTC/USDT", signal_85)
    log.info(
        f"Result for 85% confidence signal: {'Sent' if result_85 else 'Filtered'}")

    log.info("Testing signal with 95% confidence (should be sent)...")
    result_95 = await send_telegram_signal("ETH/USDT", signal_95)
    log.info(
        f"Result for 95% confidence signal: {'Sent' if result_95 else 'Filtered'}")

    log.info("Telegram test complete")

if __name__ == "__main__":
    asyncio.run(test_telegram_signal())
