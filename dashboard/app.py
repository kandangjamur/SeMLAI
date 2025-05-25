from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import pandas as pd
import os
import json
import matplotlib.pyplot as plt
import numpy as np
from io import BytesIO
import base64
from datetime import datetime, timedelta
from utils.logger import log
from flask import Flask, render_template
import logging

router = APIRouter()
templates = Jinja2Templates(directory="dashboard/templates")

app = Flask(__name__)
logger = logging.getLogger("crypto-signal-bot")

# Configure Flask app
app.config.update(
    DEBUG=True,
    TEMPLATES_AUTO_RELOAD=True
)


@router.get("/confidence", response_class=HTMLResponse)
async def confidence_statistics(request: Request):
    try:
        # Load signals data
        signals_file = "logs/signals_log.csv"
        performance_file = "logs/signal_performance.csv"
        stats = {}

        if os.path.exists(signals_file):
            signals_df = pd.read_csv(signals_file)

            if 'timestamp' in signals_df.columns:
                signals_df['timestamp'] = pd.to_datetime(
                    signals_df['timestamp'])

                # Get recent signals (last 30 days)
                recent_signals = signals_df[signals_df['timestamp'] > datetime.now(
                ) - timedelta(days=30)]

                # Calculate basic statistics
                stats["total_signals"] = len(recent_signals)
                stats["avg_confidence"] = round(
                    recent_signals['confidence'].mean(), 2)
                stats["confidence_distribution"] = get_confidence_distribution(
                    recent_signals)
                stats["timeframe_confidence"] = get_confidence_by_timeframe(
                    recent_signals)
                stats["long_short_ratio"] = get_long_short_ratio(
                    recent_signals)
                stats["confidence_chart"] = generate_confidence_chart(
                    recent_signals)

        # Load performance data if available
        performance_data = {}
        if os.path.exists(performance_file):
            perf_df = pd.read_csv(performance_file)
            performance_data["success_rate"] = round(
                perf_df['success'].mean() * 100, 2)
            performance_data["total_records"] = len(perf_df)
            performance_data["by_confidence"] = get_success_by_confidence(
                perf_df)

        return templates.TemplateResponse("confidence_stats.html", {
            "request": request,
            "stats": stats,
            "performance": performance_data,
            "last_updated": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })

    except Exception as e:
        log(f"Error generating confidence statistics: {str(e)}", level="ERROR")
        return templates.TemplateResponse("confidence_stats.html", {
            "request": request,
            "error": str(e)
        })


def get_confidence_distribution(df):
    """Get distribution of confidence scores"""
    ranges = [(0, 50), (50, 60), (60, 70), (70, 80), (80, 90), (90, 100)]
    distribution = {}

    for low, high in ranges:
        count = len(df[(df['confidence'] >= low) & (df['confidence'] < high)])
        distribution[f"{low}-{high}"] = int(count)

    return distribution


def get_confidence_by_timeframe(df):
    """Get average confidence by timeframe"""
    if 'timeframe' not in df.columns:
        return {}

    result = {}
    for timeframe, group in df.groupby('timeframe'):
        result[timeframe] = round(float(group['confidence'].mean()), 2)

    return result


def get_long_short_ratio(df):
    """Get ratio of LONG vs SHORT signals"""
    if 'direction' not in df.columns:
        return {"LONG": 0, "SHORT": 0}

    counts = df['direction'].value_counts()
    return {
        "LONG": int(counts.get("LONG", 0)),
        "SHORT": int(counts.get("SHORT", 0))
    }


def get_success_by_confidence(df):
    """Get success rate by confidence bracket"""
    if 'success' not in df.columns or 'confidence' not in df.columns:
        return {}

    df['confidence_bracket'] = pd.cut(
        df['confidence'],
        bins=[0, 50, 60, 70, 80, 90, 100],
        labels=['0-50', '50-60', '60-70', '70-80', '80-90', '90-100']
    )

    result = {}
    for bracket, group in df.groupby('confidence_bracket'):
        if len(group) >= 5:  # Only include brackets with enough data
            result[str(bracket)] = {
                "success_rate": round(group['success'].mean() * 100, 2),
                "count": len(group)
            }

    return result


def generate_confidence_chart(df):
    """Generate base64 encoded chart image of confidence over time"""
    try:
        if len(df) < 5 or 'timestamp' not in df.columns or 'confidence' not in df.columns:
            return ""

        plt.figure(figsize=(10, 6))
        plt.plot(df['timestamp'], df['confidence'],
                 marker='o', linestyle='-', alpha=0.7)
        plt.title('Signal Confidence Over Time')
        plt.xlabel('Date')
        plt.ylabel('Confidence (%)')
        plt.grid(True)
        plt.tight_layout()

        # Save to in-memory buffer
        buf = BytesIO()
        plt.savefig(buf, format='png')
        plt.close()

        # Encode as base64
        buf.seek(0)
        img_str = base64.b64encode(buf.read()).decode('utf-8')
        return f"data:image/png;base64,{img_str}"
    except Exception as e:
        log(f"Error generating confidence chart: {str(e)}", level="ERROR")
        return ""


@app.route('/')
def index():
    return render_template('index.html')


if __name__ == '__main__':
    logger.info("Starting Dashboard on port 5000...")
    app.run(host='0.0.0.0', port=5000, debug=True)
