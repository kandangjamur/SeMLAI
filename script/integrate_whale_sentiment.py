import logging
import os
import sys
import json

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


def setup_integration():
    """Set up integration of whale detection and sentiment analysis"""
    log.info("Setting up whale detection and sentiment analysis integration")

    # Ensure config directory exists
    config_dir = os.path.join(parent_dir, "config")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # Create or update confidence config
    confidence_config_path = os.path.join(config_dir, "confidence_config.json")

    # Default config
    config = {
        "telegram_minimum": 90.0,
        "base_minimum": 60.0,
        "timeframe_agreement": 2,
        "confidence_levels": {
            "low": 60.0,
            "moderate": 70.0,
            "high": 80.0,
            "very_high": 90.0
        }
    }

    # Update existing config or create new one
    if os.path.exists(confidence_config_path):
        try:
            with open(confidence_config_path, 'r') as f:
                existing_config = json.load(f)

            # Update existing config
            config.update(existing_config)
            log.info(f"Updated existing confidence config")
        except Exception as e:
            log.error(f"Error reading existing config: {str(e)}")

    # Write the config
    try:
        with open(confidence_config_path, 'w') as f:
            json.dump(config, indent=4, sort_keys=False, f)
        log.info(f"Confidence configuration saved")
    except Exception as e:
        log.error(f"Error saving confidence config: {str(e)}")

    log.info("Integration setup complete")

    # Show instructions
    print("\n---------------------------------")
    print("🐋 WHALE DETECTION & SENTIMENT ANALYSIS INTEGRATION 📰")
    print("---------------------------------")
    print("Integration is now complete! Your system will:")
    print("1. Detect whale activity patterns in trading volumes")
    print("2. Analyze news sentiment from NewsAPI.org")
    print("3. Boost confidence scores when whales and positive news align")
    print("4. Only send signals with 90%+ confidence to Telegram")
    print("5. Include whale and sentiment data in Telegram messages")
    print("---------------------------------")
    print("To adjust the minimum confidence threshold for Telegram:")
    print(f"Edit {confidence_config_path}")
    print("---------------------------------\n")


if __name__ == "__main__":
    setup_integration()
