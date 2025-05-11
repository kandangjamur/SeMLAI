import logging
import pandas as pd
from typing import Optional, Dict
from sklearn.ensemble import RandomForestClassifier
import numpy as np

class RandomForestPredictor:
    def __init__(self):
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42
        )
        self.log = logging.getLogger("crypto-signal-bot")
        self.log.info("RandomForestPredictor initialized")

    async def predict_signal(self, symbol: str, df: pd.DataFrame, timeframe: str) -> Optional[Dict]:
        try:
            # Prepare features
            features = [
                df['rsi'].iloc[-1],
                df['macd'].iloc[-1],
                df['macd_signal'].iloc[-1],
                df['bb_upper'].iloc[-1],
                df['bb_lower'].iloc[-1],
                df['atr'].iloc[-1],
                df['volume'].iloc[-1],
                df['volume_sma_20'].iloc[-1]
            ]

            # Ensure features are valid
            if any(np.isnan(f) for f in features):
                self.log.error(f"[{symbol}] Invalid features for {timeframe}: {features}")
                return None

            # Predict
            prediction = self.model.predict([features])[0]
            confidence = self.model.predict_proba([features])[0][prediction] * 100

            # Determine direction
            direction = "LONG" if prediction == 1 else "SHORT"

            self.log.info(f"[{symbol}] Prediction for {timeframe}: {direction}, Confidence: {confidence:.2f}%")

            return {
                "direction": direction,
                "confidence": confidence
            }

        except Exception as e:
            self.log.error(f"[{symbol}] Error in prediction for {timeframe}: {str(e)}")
            return None
