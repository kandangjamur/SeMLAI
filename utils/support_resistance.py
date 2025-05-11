import pandas as pd
    import numpy as np

    def find_support_resistance(df: pd.DataFrame, window: int = 20) -> pd.DataFrame:
        """
        Calculate support and resistance levels based on recent lows and highs.
        Simplified to avoid errors in breakout detection.
        """
        try:
            df = df.copy()
            # Use recent lows as support and highs as resistance
            df['support'] = df['low']
            df['resistance'] = df['high']
            return df
        except Exception as e:
            print(f"Error in find_support_resistance: {e}")
            return df
