from utils.logger import log
from model.predictor import SignalPredictor
import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)


def test_confidence_distribution():
    """Test the confidence score distribution from the enhanced predictor"""
    log("Testing confidence score distribution", level='INFO')

    # Create a predictor instance
    predictor = SignalPredictor()

    # Generate test conditions with various combinations
    conditions_sets = []
    # Generate all combinations of 6 boolean conditions
    for i in range(64):  # 2^6 = 64 combinations
        binary = format(i, '06b')
        conditions = [bit == '1' for bit in binary]
        conditions_sets.append(conditions)

    # Calculate confidence for each set of conditions
    confidences = []
    for _ in range(10):  # Run multiple times for better distribution
        for conditions in conditions_sets:
            confidence = predictor._calculate_confidence(conditions)
            confidences.append(confidence)

    # Calculate how many would meet the 90% threshold
    high_confidence = sum(1 for c in confidences if c >= 90.0)
    percentage_high = (high_confidence / len(confidences)) * 100

    # Create histogram
    plt.figure(figsize=(10, 6))
    plt.hist(confidences, bins=20, alpha=0.7, color='blue')
    plt.axvline(x=90.0, color='red', linestyle='--', label='90% Threshold')
    plt.title(f'Confidence Score Distribution (≥90%: {percentage_high:.2f}%)')
    plt.xlabel('Confidence Score')
    plt.ylabel('Frequency')
    plt.legend()

    # Save plot
    output_file = os.path.join(parent_dir, "logs/confidence_distribution.png")
    plt.savefig(output_file)
    log(f"Saved confidence distribution plot to {output_file}", level='INFO')

    # Print stats
    log(f"Total samples: {len(confidences)}", level='INFO')
    log(f"Mean confidence: {np.mean(confidences):.2f}%", level='INFO')
    log(f"Median confidence: {np.median(confidences):.2f}%", level='INFO')
    log(f"Signals ≥90%: {high_confidence} ({percentage_high:.2f}%)", level='INFO')
    log(f"Signals ≥80%: {sum(1 for c in confidences if c >= 80.0)} ({sum(1 for c in confidences if c >= 80.0) / len(confidences) * 100:.2f}%)", level='INFO')
    log(f"Signals ≥70%: {sum(1 for c in confidences if c >= 70.0)} ({sum(1 for c in confidences if c >= 70.0) / len(confidences) * 100:.2f}%)", level='INFO')
    log(f"Signals ≥60%: {sum(1 for c in confidences if c >= 60.0)} ({sum(1 for c in confidences if c >= 60.0) / len(confidences) * 100:.2f}%)", level='INFO')


if __name__ == "__main__":
    test_confidence_distribution()
