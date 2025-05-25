import os
import asyncio
import httpx
import json
import logging
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env')
load_dotenv('config.env')

# Get logger
logger = logging.getLogger("crypto-signal-bot")

# Get Telegram bot token and chat ID from environment variables
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "true").lower() == "true"

# Load confidence threshold from config
try:
    config_path = os.path.join('config', 'confidence_config.json')
    if os.path.exists(config_path):
        with open(config_path, 'r') as f:
            CONFIDENCE_CONFIG = json.load(f)
        MINIMUM_TELEGRAM_CONFIDENCE = CONFIDENCE_CONFIG.get(
            'telegram_minimum', 95.0)
    else:
        MINIMUM_TELEGRAM_CONFIDENCE = 95.0
except Exception as e:
    logger.error(f"Error loading confidence config: {str(e)}")
    MINIMUM_TELEGRAM_CONFIDENCE = 95.0


async def send_telegram_signal(symbol, signal):
    """Send signal to Telegram chat"""
    if not TELEGRAM_ENABLED:
        logger.info(f"Telegram notifications disabled")
        return False

    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.error("Telegram bot token or chat ID not configured")
        return False

    try:
        # Check if signal meets minimum confidence threshold
        confidence = signal.get('confidence', 0)
        if confidence < MINIMUM_TELEGRAM_CONFIDENCE:
            logger.info(
                f"[{symbol}] Signal has {confidence:.2f}% confidence, below threshold of {MINIMUM_TELEGRAM_CONFIDENCE:.2f}%")
            return False

        # Ensure required fields exist
        for field in ['tp1_possibility', 'tp2_possibility', 'tp3_possibility', 'whale_activity']:
            if field not in signal:
                if 'possibility' in field:
                    signal[field] = 0.7 if 'tp1' in field else 0.5 if 'tp2' in field else 0.3
                elif field == 'whale_activity':
                    signal[field] = 'No'

        # Format message
        direction = signal['direction']
        emoji = "🟢" if direction == "LONG" else "🔴"

        # Add emoji indicators
        whale_emoji = "🐋 " if signal.get('whale_activity') == "Yes" else ""

        # Add sentiment emoji
        sentiment = signal.get('news_sentiment', 'neutral')
        sentiment_emoji = ""
        if sentiment == 'positive':
            sentiment_emoji = "📈 "
        elif sentiment == 'negative':
            sentiment_emoji = "📉 "

        # Add ML emoji
        ml_direction = signal.get('ml_prediction')
        ml_emoji = ""
        if ml_direction == direction:  # ML agrees with signal
            ml_emoji = "🧠 "

        # Format message with high confidence alert
        message = f"*{emoji} {whale_emoji}{sentiment_emoji}{ml_emoji}HIGH CONFIDENCE SIGNAL: {symbol} {direction}*\n\n"
        message += f"*Timeframe:* {signal.get('timeframe', '1h')}\n"
        message += f"*Confidence:* {confidence:.2f}%\n"
        message += f"*Entry:* {signal['entry']}\n"
        message += f"*Stop Loss:* {signal['sl']}\n\n"
        message += f"*Take Profit 1:* {signal['tp1']} ({signal['tp1_possibility']*100:.0f}%)\n"
        message += f"*Take Profit 2:* {signal['tp2']} ({signal['tp2_possibility']*100:.0f}%)\n"
        message += f"*Take Profit 3:* {signal['tp3']} ({signal['tp3_possibility']*100:.0f}%)\n\n"

        # Calculate risk/reward ratio
        entry = float(signal['entry'])
        sl = float(signal['sl'])
        tp1 = float(signal['tp1'])
        risk_reward = round(abs((tp1 - entry) / (entry - sl)),
                            2) if abs(entry - sl) > 0 else 0

        message += f"*Risk/Reward:* {risk_reward}\n\n"

        # Add additional signal factors section
        message += "*Signal Factors:*\n"

        # Add whale activity info if present
        if signal.get('whale_activity') == "Yes":
            whale_type = signal.get('whale_type', '').replace('_', ' ').title()
            message += f"🐋 *Whale Activity:* {whale_type} ({signal.get('whale_score', 0)}%)\n"

        # Add sentiment info
        sentiment_score = signal.get('news_score', 0)
        sentiment_score_str = f"{sentiment_score:.2f}" if sentiment_score else "N/A"
        message += f"📰 *News Sentiment:* {sentiment.capitalize()} ({sentiment_score_str})\n"

        # Add ML prediction info
        ml_confidence = signal.get('ml_confidence', 0)
        ml_direction = signal.get('ml_prediction')
        ml_patterns = signal.get('candlestick_patterns', [])
        if ml_direction:
            ml_agreement = "✓ Agrees" if ml_direction == direction else "✗ Disagrees"
            message += f"🧠 *ML Prediction:* {ml_direction} ({ml_confidence:.2f}%) {ml_agreement}\n"

            # Add candlestick pattern info if available
            if ml_patterns:
                message += f"📊 *Patterns:* {', '.join(ml_patterns)}\n"

        # Add headlines if available
        if 'headlines' in signal and signal['headlines']:
            message += "\n*Recent Headlines:*\n"
            for i, headline in enumerate(signal['headlines'][:2], 1):
                title = headline.get('title', '')
                sentiment_icon = "📈" if headline.get(
                    'sentiment') == 'positive' else "📉" if headline.get('sentiment') == 'negative' else "📊"
                if len(title) > 80:
                    title = title[:77] + "..."
                message += f"{sentiment_icon} {title}\n"

        message += f"\n*Time:* {signal.get('timestamp', 'now')}"

        # Add disclaimer
        message += "\n\n_This is an automated signal and not financial advice. Always do your own research._"

        # Send message
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        params = {
            "chat_id": TELEGRAM_CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, params=params)

        if response.status_code == 200:
            logger.info(f"[{symbol}] HIGH CONFIDENCE signal sent to Telegram")
            return True
        else:
            logger.error(f"Failed to send Telegram message: {response.text}")
            return False

    except Exception as e:
        logger.error(f"Error sending Telegram message: {str(e)}")
        return False
