import os
import sys
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(name)s | %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
log = logging.getLogger("crypto-signal-bot")


def setup_sentiment_whale():
    """Set up sentiment analysis and whale detection integration"""
    log.info("Setting up sentiment analysis and whale detection integration")

    # Ensure config directory exists
    config_dir = 'config'
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)
        log.info(f"Created {config_dir} directory")

    # Create confidence configuration
    confidence_config = {
        "telegram_minimum": 90.0,
        "base_minimum": 70.0,
        "confidence_levels": {
            "low": 60.0,
            "medium": 70.0,
            "high": 80.0,
            "very_high": 90.0
        },
        "whale_detection": {
            "enable": True,
            "volume_spike_threshold": 2.0,
            "abnormal_volume_threshold": 3.0,
            "minimal_price_move_threshold": 1.0
        },
        "sentiment_analysis": {
            "enable": True,
            "days_lookback": 2,
            "positive_boost": 15.0,
            "negative_penalty": 15.0
        }
    }

    # Write configuration to file
    config_path = os.path.join(config_dir, 'confidence_config.json')
    with open(config_path, 'w') as f:
        json.dump(confidence_config, f, indent=4)

    log.info(f"Created confidence configuration at {config_path}")

    # Create empty __init__.py files if they don't exist
    dirs_to_initialize = ['core', 'model', 'telebot']
    for dir_name in dirs_to_initialize:
        init_file = os.path.join(dir_name, '__init__.py')
        if not os.path.exists(init_file):
            with open(init_file, 'w') as f:
                f.write("# Initialize package\n")
            log.info(f"Created {init_file}")

    log.info("Setup complete!")
    log.info(
        "Your system is now configured to use both news sentiment and whale detection.")
    log.info(f"Only signals with confidence of 90%+ will be sent to Telegram.")


if __name__ == "__main__":
    setup_sentiment_whale()
