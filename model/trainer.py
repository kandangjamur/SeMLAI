import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
import joblib
import os

MODEL_SAVE_PATH = "model/signal_model.pkl"
HISTORICAL_DATA_PATH = "data/historical_signals.csv"  # CSV with features + labels

def load_training_data():
    """Load historical signal dataset with features and labels."""
    if not os.path.exists(HISTORICAL_DATA_PATH):
        raise FileNotFoundError("Historical data file not found.")

    df = pd.read_csv(HISTORICAL_DATA_PATH)
    
    # Drop rows with missing values
    df.dropna(inplace=True)

    X = df[[
        "rsi", "macd", "macd_signal", "ema_fast", "ema_slow",
        "volume", "price_change", "whale_alert", "sentiment_score"
    ]]
    y = df["label"]  # buy/sell/hold

    return train_test_split(X, y, test_size=0.2, random_state=42)

def train_model():
    """Train a RandomForest model and save it."""
    X_train, X_test, y_train, y_test = load_training_data()

    model = RandomForestClassifier(n_estimators=200, random_state=42)
    model.fit(X_train, y_train)

    predictions = model.predict(X_test)
    acc = accuracy_score(y_test, predictions)
    print("Accuracy:", round(acc * 100, 2), "%")
    print(classification_report(y_test, predictions))

    # Save model
    joblib.dump(model, MODEL_SAVE_PATH)
    print(f"Model saved to: {MODEL_SAVE_PATH}")

if __name__ == "__main__":
    train_model()
