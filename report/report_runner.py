from report.sender import send_daily_report
from utils.logger import log
import schedule
import time
from datetime import datetime, timedelta
import signal
import sys
import os

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.append(project_root)


def signal_handler(signum, frame):
    """Handle shutdown signals gracefully"""
    log("Shutting down report scheduler...", level="INFO")
    sys.exit(0)


def run_scheduler():
    try:
        log("📅 Report scheduler started...")

        # Schedule report for 11:59 PM Pakistan Time (GMT+5)
        schedule.every().day.at("18:59").do(send_daily_report)
        log("Daily report scheduled for 11:59 PM PKT")

        # Register signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

        while True:
            try:
                schedule.run_pending()
                time.sleep(30)
            except Exception as e:
                log(f"Error in scheduler loop: {e}", level="ERROR")
                time.sleep(60)  # Wait a minute before retrying
    except Exception as e:
        log(f"Fatal error in scheduler: {e}", level="ERROR")
        raise


if __name__ == "__main__":
    try:
        run_scheduler()
    except KeyboardInterrupt:
        log("Report scheduler stopped by user", level="INFO")
    except Exception as e:
        log(f"Report scheduler failed: {e}", level="ERROR")
        sys.exit(1)
