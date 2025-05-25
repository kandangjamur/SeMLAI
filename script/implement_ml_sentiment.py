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
    """Set up integration of ML prediction and sentiment analysis"""
    log.info("Setting up ML prediction and news sentiment integration")

    # Ensure config directory exists
    config_dir = os.path.join(parent_dir, "config")
    if not os.path.exists(config_dir):
        os.makedirs(config_dir)

    # Create models directory for ML models
    models_dir = os.path.join(parent_dir, "models")
    if not os.path.exists(models_dir):
        os.makedirs(models_dir)

    # Create or update confidence config
    confidence_config_path = os.path.join(config_dir, "confidence_config.json")

    # Default config
    config = {
        "telegram_minimum": 90.0,
        "base_minimum": 70.0,
        "indicators": {
            "rsi": 0.12,
            "macd": 0.12,
            "volume": 0.10,
            "bollinger": 0.10,
            "atr": 0.05,
            "support_resistance": 0.12,
            "whale_activity": 0.15,
            "sentiment": 0.12,
            "ml_prediction": 0.12
        },
        "sentiment_analysis": {
            "enabled": True,
            "days_lookback": 2,
            "boost_factor": 1.0
        },
        "ml_prediction": {
            "enabled": True,
            "model_path": "models/random_forest_model.joblib",
            "boost_factor": 1.0
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
            json.dump(config, f, indent=4, sort_keys=False)
        log.info(f"Confidence configuration saved")
    except Exception as e:
        log.error(f"Error saving confidence config: {str(e)}")

    log.info("Integration setup complete")

    # Show instructions
    print("\n---------------------------------")
    print("🧠 ML PREDICTION & NEWS SENTIMENT INTEGRATION 📰")
    print("---------------------------------")
    print("Integration is now complete! Your system will:")
    print("1. Use ML predictions as an additional indicator")
    print("2. Properly apply news sentiment based on LONG/SHORT direction")
    print("3. Boost confidence when ML predictions and news sentiment align")
    print("4. Only send signals with 90%+ confidence to Telegram")
    print("5. Include ML predictions and sentiment data in Telegram messages")
    print("---------------------------------")
    print("To adjust the minimum confidence threshold for Telegram:")
    print(f"Edit {confidence_config_path}")
    print("---------------------------------\n")
    print("IMPORTANT: News sentiment is now properly applied:")
    print("- Positive news BOOSTS LONG signals and REDUCES SHORT signals")
    print("- Negative news BOOSTS SHORT signals and REDUCES LONG signals")
    print("---------------------------------\n")


if __name__ == "__main__":
    setup_integration()
