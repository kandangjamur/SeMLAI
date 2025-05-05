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

        # فلٹرز: 0 ویلیو، کم حجم، کم کنفیڈنس ہٹائیں
        today_signals = df[
            (df['timestamp'].dt.date == today) & 
            (df['entry'] > 0) & 
            (df['tp1'] > 0) & 
            (df['tp2'] > 0) & 
            (df['tp3'] > 0) & 
            (df['sl'] > 0) & 
            (df['volume'] >= 100000) & 
            (df['confidence'] >= 80) & 
            (df['tp1_chance'] >= 75)
        ]
        if today_signals.empty:
            summary = f"📋 *Daily Report ({today})*\n\nNo valid signals generated today."
            await send_telegram_message(summary)
            log("📈 Daily Report Sent (No signals)")
            return

        total = len(today_signals)
        long_signals = len(today_signals[today_signals['direction'] == 'LONG'])
        short_signals = len(today_signals[today_signals['direction'] == 'SHORT'])
        scalping_signals = len(today_signals[today_signals['timeframe'].isin(['15m', '1h'])])
        normal_signals = len(today_signals[today_signals['timeframe'].isin(['4h', '1d'])])
        tp1_hits = len(today_signals[today_signals['status'] == 'tp1'])
        tp2_hits = len(today_signals[today_signals['status'] == 'tp2'])
        tp3_hits = len(today_signals[today_signals['status'] == 'tp3'])
        sl_hits = len(today_signals[today_signals['status'] == 'sl'])

        total_hits = tp1_hits + tp2_hits + tp3_hits
        accuracy = round((total_hits / total * 100) if total > 0 else 0, 2)

        # TP1، TP2، TP3 کی اوسط امکان
        avg_tp1_chance = round(today_signals['tp1_chance'].mean(), 2) if 'tp1_chance' in today_signals.columns else 0
        avg_tp2_chance = round(today_signals['tp2_chance'].mean(), 2) if 'tp2_chance' in today_signals.columns else 0
        avg_tp3_chance = round(today_signals['tp3_chance'].mean(), 2) if 'tp3_chance' in today_signals.columns else 0

        # ٹاپ جوڑوں کی کارکردگی
        successful_pairs = today_signals[today_signals['status'].isin(['tp1', 'tp2', 'tp3'])]
        top_pairs = successful_pairs['symbol'].value_counts().head(3).to_dict()
        top_pairs_str = "\n".join([f"{symbol}: {count} hits" for symbol, count in top_pairs.items()]) if top_pairs else "None"

        # انڈیکیٹرز اور بیک ٹیسٹنگ
        indicators_used = today_signals['indicators'].value_counts().head(3).to_dict() if 'indicators' in today_signals.columns else {"N/A": 0}
        indicators_str = "\n".join([f"{ind}: {count} signals" for ind, count in indicators_used.items()])
        backtest_success = len(today_signals[today_signals['backtest_result'] == 'SUCCESS']) if 'backtest_result' in today_signals.columns else 0
        backtest_rate = round((backtest_success / total * 100) if total > 0 else 0, 2)

        # 0 ویلیو سگنلز لاگ کریں
        zero_signals = df[(df['timestamp'].dt.date == today) & ((df['entry'] == 0) | (df['tp1'] == 0) | (df['tp2'] == 0) | (df['tp3'] == 0) | (df['sl'] == 0))]
        if not zero_signals.empty:
            zero_signals.to_csv("logs/zero_value_errors.csv", index=False)
            log(f"Logged {len(zero_signals)} zero-value signals", level='WARNING')

        summary = (
            f"📋 *Daily Report ({today})*\n\n"
            f"📊 *Total Signals*: {total}\n"
            f"🔼 *LONG Signals*: {long_signals}\n"
            f"🔽 *SHORT Signals*: {short_signals}\n"
            f"⚡ *Scalping Signals (15m/1h)*: {scalping_signals}\n"
            f"📈 *Normal Signals (4h/1d)*: {normal_signals}\n"
            f"🎯 *TP1 Hits*: {tp1_hits} (Avg Chance: {avg_tp1_chance}%)\n"
            f"🎯 *TP2 Hits*: {tp2_hits} (Avg Chance: {avg_tp2_chance}%)\n"
            f"🎯 *TP3 Hits*: {tp3_hits} (Avg Chance: {avg_tp3_chance}%)\n"
            f"🛑 *SL Hits*: {sl_hits}\n"
            f"✅ *Accuracy*: {accuracy}%\n"
            f"🏆 *Top Pairs*:\n{top_pairs_str}\n"
            f"📡 *Indicators Used*:\n{indicators_str}\n"
            f"🔍 *Backtest Success Rate*: {backtest_rate}%\n"
            f"🕒 *Generated*: {datetime.now(pytz.timezone('Asia/Karachi')).strftime('%Y-%m-%d %H:%M:%S')}"
        )

        # رپورٹ CSV میں محفوظ کریں
        csv_path = "logs/daily_reports.csv"
        report_data = {
            "date": str(today),
            "total_signals": total,
            "long_signals": long_signals,
            "short_signals": short_signals,
            "scalping_signals": scalping_signals,
            "normal_signals": normal_signals,
            "tp1_hits": tp1_hits,
            "tp1_chance": avg_tp1_chance,
            "tp2_hits": tp2_hits,
            "tp2_chance": avg_tp2_chance,
            "tp3_hits": tp3_hits,
            "tp3_chance": avg_tp3_chance,
            "sl_hits": sl_hits,
            "accuracy": accuracy,
            "top_pairs": str(top_pairs),
            "indicators": str(indicators_used),
            "backtest_rate": backtest_rate,
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
        log_report_status(False, str(e))

if __name__ == "__main__":
    asyncio.run(generate_daily_summary())
