import os
import json
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger()


def update_config():
    """Update confidence configuration to fix the cap"""
    try:
        config_dir = 'config'
        config_path = os.path.join(config_dir, 'confidence_config.json')

        # Create directory if it doesn't exist
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)
            logger.info(f"Created directory: {config_dir}")

        # Default config
        config = {
            "telegram_minimum": 90.0,
            "base_minimum": 70.0,
            "confidence_cap": 98.0,
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
            },
            "boost_caps": {
                "multiple_indicators": 20.0,
                "whale_activity": 12.0,
                "sentiment": 8.0,
                "ml_prediction": 10.0,
                "triple_confirmation": 15.0,
                "double_confirmation": 12.0
            }
        }

        # Update existing config if it exists
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r') as f:
                    existing_config = json.load(f)

                # Add missing keys while keeping existing values
                for key, value in config.items():
                    if key not in existing_config:
                        existing_config[key] = value
                    elif isinstance(value, dict) and isinstance(existing_config[key], dict):
                        # Merge nested dictionaries
                        for subkey, subvalue in value.items():
                            if subkey not in existing_config[key]:
                                existing_config[key][subkey] = subvalue

                config = existing_config
                logger.info("Updated existing configuration")

            except Exception as e:
                logger.error(f"Error reading existing config: {str(e)}")

        # Ensure confidence cap is set
        if "confidence_cap" not in config:
            config["confidence_cap"] = 98.0

        # Add boost caps if not present
        if "boost_caps" not in config:
            config["boost_caps"] = {
                "multiple_indicators": 20.0,
                "whale_activity": 12.0,
                "sentiment": 8.0,
                "ml_prediction": 10.0,
                "triple_confirmation": 15.0,
                "double_confirmation": 12.0
            }

        # Write updated config
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=4)

        logger.info(f"Configuration saved to {config_path}")
        return True

    except Exception as e:
        logger.error(f"Error updating config: {str(e)}")
        return False


if __name__ == "__main__":
    logger.info("Updating confidence configuration...")
    success = update_config()

    if success:
        logger.info("Configuration updated successfully")
    else:
        logger.error("Failed to update configuration")
