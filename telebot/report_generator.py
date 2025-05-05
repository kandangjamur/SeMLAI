import pandas as pd
import httpx
import asyncio
from datetime import datetime
import pytz
import os
from utils.logger import log

BOT_TOKEN = "7620836100:AAEEe4yAP18Lxxj0HoYfH8aeX4PetAxYsV0"
CHAT_ID = "-4694205383"

async def send_telegram_message(message: str):
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            "chat_id": CHAT_ID,
            "text": message,
            "parse_mode": "Markdown"
        }

        async with httpx.AsyncClient() as client:
            for attempt in range(3):
                try:
                    response = await client.post(url, json=payload)
                    if response.status_code == 200:
                        log("Telegram message sent successfully")
                        log_report_status(True, "Success")
                        return
                    else:
                        log(f"Failed to send Telegram message: {response.text}", level='ERROR')
                        log_report_status(False, response.text)
                except Exception as e:
                    log(f"Error sending Telegram message: {e}", level='ERROR')
                    log_report_status(False, str(e))
                await asyncio.sleep(2)

            # Log failure after 3 attempts, no admin alert
            log("Failed to send daily report after 3 attempts", level='ERROR')

    except Exception as e:
        log(f"Error in send_telegram_message: {e}", level='ERROR')
        log_report_status(False, str(e))

def log_report_status(success: bool, message: str):
    try:
        csv_path = "logs/report_status.csv"
        timestamp = datetime.now(pytz.timezone('Asia/Karachi')).strftime('%Y-%m-%d %H:%M:%S')
        data = {
            "success": success,
            "message": message,
            "timestamp": timestamp
        }
        df = pd.DataFrame([data])

        if os.path.exists(csv_path):
            old_df = pd.read_csv(csv_path)
            if not df.empty and not df.isna().all().all():
                df = pd.concat([old_df, df], ignore_index=True)

        if not df.empty and not df.isna().all().all():
            df.to_csv(csv_path, index=False)
            log(f"Report status logged: Success={success}")
        else:
            log("No valid data to log report status", level='ERROR')
    except Exception as e:
        log(f"Error logging report status: {e}", level='ERROR')

async def generate_daily_summary():
    try:
        df = pd.read_csv("logs/signals_log.csv")
        today = datetime.now(pytz.timezone('Asia/Karachi')).date()
        df['timestamp'] = pd.to_datetime(df['timestamp'])

        today_signals = df[df['timestamp'].dt.date == today]
        if today_signals.empty:
            summary = f"📋 *Daily Report ({today})*\n\nNo signals generated today."
            await send_telegram_message(summary)
            log("📈 Daily Report Sent (No signals)")
            return

        total = len(today_signals)
        long_signals = len(today_signals[today_signals['direction'] == 'LONG'])
        short_signals = len(today_signals[today_signals['direction'] == 'SHORT'])
        tp1_hits = len(today_signals[today_signals['status'] == 'tp1'])
        tp2_hits = len(today_signals[today_signals['status'] == 'tp2'])
        tp3_hits = len(today_signals[today_signals['status'] == 'tp3'])
        sl_hits = len(today_signals[today_signals['status'] == 'sl'])

        total_hits = tp1_hits + tp2_hits + tp3_hits
        accuracy = round((total_hits / total * 100) if total > 0 else 0, 2)

        # Top performing pairs
        successful_pairs = today_signals[today_signals['status'].isin(['tp1', 'tp2', 'tp3'])]
        top_pairs = successful_pairs['symbol'].value_counts().head(3).to_dict()
        top_pairs_str = "\n".join([f"{symbol}: {count} hits" for symbol, count in top_pairs.items()]) if top_pairs else "None"

        summary = (
            f"📋 *Daily Report ({today})*\n\n"
            f"📊 *Total Signals*: {total}\n"
            f"🔼 *LONG Signals*: {long_signals}\n"
            f"🔽 *SHORT Signals*: {short_signals}\n"
            f"🎯 *TP1 Hits*: {tp1_hits}\n"
            f"🎯 *TP2 Hits*: {tp2_hits}\n"
            f"🎯 *TP3 Hits*: {tp3_hits}\n"
            f"🛑 *SL Hits*: {sl_hits}\n"
            f"✅ *Accuracy*: {accuracy}%\n"
            f"🏆 *Top Pairs*:\n{top_pairs_str}\n"
            f"🕒 *Generated*: {datetime.now(pytz.timezone('Asia/Karachi')).strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # Save report to CSV
        csv_path = "logs/daily_reports.csv"
        report_data = {
            "date": str(today),
            "total_signals": total,
            "long_signals": long_signals,
            "short_signals": short_signals,
            "tp1_hits": tp1_hits,
            "tp2_hits": tp2_hits,
            "tp3_hits": tp3_hits,
            "sl_hits": sl_hits,
            "accuracy": accuracy,
            "top_pairs": str(top_pairs),
            "timestamp": datetime.now(pytz.timezone('Asia/Karachi')).strftime('%Y-%m-%d %H:%M:%S')
        }
        report_df = pd.DataFrame([report_data])

        if os.path.exists(csv_path):
            old_df = pd.read_csv(csv_path)
            if not report_df.empty and not report_df.isna().all().all():
                report_df = pd.concat([old_df, report_df], ignore_index=True)

        if not report_df.empty and not report_df.isna().all().all():
            report_df.to_csv(csv_path, index=False)
            log("Daily report saved to CSV")

        await send_telegram_message(summary)
        log("📈 Daily Report Sent")

    except Exception as e:
        log(f"❌ Report Error: {e}", level='ERROR')
        log_report_status(False, str(e)) isme pakistan time set hy isko yehi rehne dena hy or iska msg dikhao mjhje kese show hoga telegaram per or mene kaha tha code likhne na beth jaya kro jb tak me na kaho  or mukhtisir bat kia kro
