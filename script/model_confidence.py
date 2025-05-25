from model.predictor import SignalPredictor
from utils.logger import log
import os
import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def analyze_indicator_impact():
    """Analyze the impact of different indicators on signal generation"""

    predictor = SignalPredictor()

    # Default weights
    original_weights = predictor.indicator_weights.copy()

    # Test cases with different weight distributions
    test_cases = [
        {"name": "Equal Weights", "weights": {"rsi": 0.2, "macd": 0.2,
                                              "volume": 0.2, "bollinger": 0.2, "atr": 0.1, "support_resistance": 0.1}},
        {"name": "RSI Heavy", "weights": {"rsi": 0.5, "macd": 0.1, "volume": 0.1,
                                          "bollinger": 0.1, "atr": 0.1, "support_resistance": 0.1}},
        {"name": "MACD Heavy", "weights": {"rsi": 0.1, "macd": 0.5, "volume": 0.1,
                                           "bollinger": 0.1, "atr": 0.1, "support_resistance": 0.1}},
        {"name": "Volume Heavy", "weights": {"rsi": 0.1, "macd": 0.1,
                                             "volume": 0.5, "bollinger": 0.1, "atr": 0.1, "support_resistance": 0.1}},
        {"name": "Bollinger Heavy", "weights": {"rsi": 0.1, "macd": 0.1,
                                                "volume": 0.1, "bollinger": 0.5, "atr": 0.1, "support_resistance": 0.1}},
        {"name": "S/R Heavy", "weights": {"rsi": 0.1, "macd": 0.1, "volume": 0.1,
                                          "bollinger": 0.1, "atr": 0.1, "support_resistance": 0.5}}
    ]

    # Signals file
    signals_file = "logs/signals_log.csv"
    if not os.path.exists(signals_file):
        log("Signals log file not found", level='ERROR')
        return

    # Load signals
    df = pd.read_csv(signals_file)
    log(f"Loaded {len(df)} signals for analysis", level='INFO')

    # Test different weight configurations
    results = []

    for case in test_cases:
        # Apply weights to predictor
        for key, value in case["weights"].items():
            predictor.indicator_weights[key] = value

        # Calculate how many signals would be generated with these weights
        threshold = 70.0  # Confidence threshold

        # Count signals with sufficient confidence
        signals_count = 0
        profit_rate = 0

        # Analyze recent signals (last 30 days)
        df['timestamp'] = pd.to_datetime(df['timestamp'], errors='coerce')
        recent_df = df[df['timestamp'] > datetime.now() - timedelta(days=30)]

        for _, signal in recent_df.iterrows():
            # Simple approximation - recalculate confidence based on indicators
            conditions = {
                "rsi": signal.get('rsi', 0) > 70 or signal.get('rsi', 0) < 30,
                "macd": signal.get('macd', 0) > signal.get('macdsignal', 0),
                "volume": signal.get('volume', 0) > signal.get('volume_sma20', 0) * 1.5 if 'volume_sma20' in signal else False,
                "bollinger": signal.get('close', 0) > signal.get('upper_band', 0) or signal.get('close', 0) < signal.get('lower_band', 0),
                "support_resistance": True  # Simplified, assume true for test
            }

            # Calculate weighted confidence
            conf = 10  # Base confidence
            for indicator, condition in conditions.items():
                if condition:
                    conf += case["weights"][indicator] * 100

            if conf >= threshold:
                signals_count += 1

                # Calculate profitability rate (simplified)
                if signal.get('status') in ['tp1', 'tp2', 'tp3']:
                    profit_rate += 1

        # Calculate profitability as a percentage
        profit_pct = (profit_rate / signals_count *
                      100) if signals_count > 0 else 0

        results.append({
            "name": case["name"],
            "signals": signals_count,
            "profit_rate": profit_pct
        })

        log(f"{case['name']} would generate {signals_count} signals with {profit_pct:.2f}% profitability")

    # Create a bar chart of results
    plt.figure(figsize=(12, 6))
    names = [r["name"] for r in results]
    signals = [r["signals"] for r in results]
    profits = [r["profit_rate"] for r in results]

    x = np.arange(len(names))
    width = 0.35

    fig, ax = plt.subplots(figsize=(14, 7))
    rects1 = ax.bar(x - width/2, signals, width, label='Signals Generated')
    rects2 = ax.bar(x + width/2, profits, width, label='Profit Rate (%)')

    ax.set_title(
        'Impact of Indicator Weights on Signal Generation and Profitability')
    ax.set_xticks(x)
    ax.set_xticklabels(names, rotation=45, ha='right')
    ax.legend()

    fig.tight_layout()

    # Save plot
    plt.savefig('logs/indicator_impact.png')
    log("Indicator impact analysis saved to logs/indicator_impact.png", level='INFO')

    # Restore original weights
    predictor.indicator_weights = original_weights


if __name__ == "__main__":
    analyze_indicator_impact()
