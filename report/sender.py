import asyncio
from utils.logger import log
from telebot.report_generator import generate_daily_summary
import os
import sys

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)


async def _send_daily_report():
    try:
        log("Generating daily report...")
        await generate_daily_summary()
    except Exception as e:
        log(f"Error sending daily report: {e}", level="ERROR")


def send_daily_report():
    """
    Synchronous wrapper for the async report generation function.
    This is needed because the scheduler runs synchronous functions.
    """
    try:
        asyncio.run(_send_daily_report())
    except Exception as e:
        log(f"Error in send_daily_report: {e}", level="ERROR")
