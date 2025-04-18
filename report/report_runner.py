import schedule
import time
from datetime import datetime, timedelta
from report.sender import send_daily_report
from utils.logger import log

def schedule():
    log("📅 Report scheduler started...")

    # Adjust this for GMT+5 offset — run at UTC 18:59 == 11:59 PM GMT+5
    schedule.every().day.at("18:59").do(send_daily_report)

    while True:
        schedule.run_pending()
        time.sleep(30)
