import os
from dotenv import load_dotenv

# Load environment variables from config.env
load_dotenv('config.env')


def get_telegram_config():
    """Get Telegram bot configuration from environment variables"""
    bot_token = os.getenv('TELEGRAM_BOT_TOKEN')
    chat_id = os.getenv('TELEGRAM_CHAT_ID')

    if not bot_token or not chat_id:
        raise ValueError(
            "TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in config.env")

    return bot_token, chat_id
