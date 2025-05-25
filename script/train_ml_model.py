import os
import sys
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split, TimeSeriesSplit
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib
import ccxt
import logging
import traceback
from datetime import datetime, timedelta
from core.candle_patterns import (
    is_bullish_engulfing, is_bearish_engulfing, is_doji,
    is_hammer, is_shooting_star, is_three_white_soldiers,
    is_three_black_crows
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger()

# Add parent directory to path
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(parent_dir)

# Ensure models directory exists
os.makedirs('models', exist_ok=True)


def fetch_training_data(symbols=['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'DOGE/USDT', 'LINK/USDT', 'AVAX/USDT', 'ADA/USDT', 'XRP/USDT'],
                        timeframe='1h', limit=500):
    """Fetch historical data for training"""
    try:
        exchange = ccxt.binance({
            'enableRateLimit': True
        })

        datasets = []

        for symbol in symbols:
            logger.info(f"Fetching data for {symbol}")
            ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
            df = pd.DataFrame(
                ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
            df['symbol'] = symbol

            # Calculate future price change (target)
            df['future_price'] = df['close'].shift(-5)  # 5 candles ahead
            df['price_change_pct'] = (
                df['future_price'] - df['close']) / df['close'] * 100

            # Define target: 1 for price rise, 0 for flat or down
            df['target'] = np.where(df['price_change_pct'] > 1, 1, 0)

            datasets.append(df)

        all_data = pd.concat(datasets)
        all_data = all_data.dropna()

        return all_data

    except Exception as e:
        logger.error(f"Error fetching data: {str(e)}")
        logger.error(traceback.format_exc())
        return None


def calculate_candlestick_patterns(df):
    """Calculate candlestick patterns directly without using .apply()"""
    # Make sure df has unique index
    df = df.reset_index(drop=True)

    # Initialize pattern columns
    pattern_columns = [
        'bullish_engulfing', 'bearish_engulfing', 'doji',
        'hammer', 'shooting_star', 'three_white_soldiers', 'three_black_crows'
    ]
    for col in pattern_columns:
        df[col] = 0.0

    # Calculate patterns for each valid position
    for i in range(1, len(df)):  # Start from 1 (need previous candle)
        # Doji pattern
        body = abs(df.loc[i, 'close'] - df.loc[i, 'open'])
        candle_range = df.loc[i, 'high'] - df.loc[i, 'low']
        if candle_range > 0 and body / candle_range < 0.1:
            df.loc[i, 'doji'] = 1.0

        # Bullish Engulfing
        prev_bearish = df.loc[i-1, 'close'] < df.loc[i-1, 'open']
        curr_bullish = df.loc[i, 'close'] > df.loc[i, 'open']
        body_engulfing = (df.loc[i, 'open'] <= df.loc[i-1, 'close']
                          ) and (df.loc[i, 'close'] >= df.loc[i-1, 'open'])
        if prev_bearish and curr_bullish and body_engulfing:
            df.loc[i, 'bullish_engulfing'] = 1.0

        # Bearish Engulfing
        prev_bullish = df.loc[i-1, 'close'] > df.loc[i-1, 'open']
        curr_bearish = df.loc[i, 'close'] < df.loc[i, 'open']
        body_engulfing = (df.loc[i, 'close'] <= df.loc[i-1, 'open']
                          ) and (df.loc[i, 'open'] >= df.loc[i-1, 'close'])
        if prev_bullish and curr_bearish and body_engulfing:
            df.loc[i, 'bearish_engulfing'] = 1.0

        # Calculate body and shadows for hammer and shooting star
        body = abs(df.loc[i, 'close'] - df.loc[i, 'open'])
        upper_shadow = df.loc[i, 'high'] - \
            max(df.loc[i, 'open'], df.loc[i, 'close'])
        lower_shadow = min(df.loc[i, 'open'],
                           df.loc[i, 'close']) - df.loc[i, 'low']

        # Hammer - small body, long lower shadow
        if body > 0:
            body_range_ratio = body / (df.loc[i, 'high'] - df.loc[i, 'low'])
            lower_body_ratio = lower_shadow / body
            if body_range_ratio < 0.3 and lower_body_ratio > 2.0 and upper_shadow < body:
                df.loc[i, 'hammer'] = 1.0

        # Shooting Star - small body, long upper shadow
        if body > 0:
            body_range_ratio = body / (df.loc[i, 'high'] - df.loc[i, 'low'])
            upper_body_ratio = upper_shadow / body
            if body_range_ratio < 0.3 and upper_body_ratio > 2.0 and lower_shadow < body:
                df.loc[i, 'shooting_star'] = 1.0

    # Three White Soldiers and Three Black Crows require at least 3 previous candles
    for i in range(3, len(df)):
        # Three White Soldiers
        bullish_candles = all(
            [df.loc[i-j, 'close'] > df.loc[i-j, 'open'] for j in range(3)])
        higher_closes = df.loc[i, 'close'] > df.loc[i -
                                                    1, 'close'] > df.loc[i-2, 'close']
        higher_opens = df.loc[i, 'open'] > df.loc[i -
                                                  1, 'open'] > df.loc[i-2, 'open']

        if bullish_candles and higher_closes and higher_opens:
            # Check for substantial bodies with small upper shadows
            bodies = [abs(df.loc[i-j, 'close'] - df.loc[i-j, 'open'])
                      for j in range(3)]
            ranges = [df.loc[i-j, 'high'] - df.loc[i-j, 'low']
                      for j in range(3)]
            upper_shadows = [
                df.loc[i-j, 'high'] - max(df.loc[i-j, 'open'], df.loc[i-j, 'close']) for j in range(3)]

            good_bodies = all([bodies[j] / ranges[j] > 0.5 for j in range(3)])
            small_shadows = all(
                [upper_shadows[j] / bodies[j] < 0.3 for j in range(3)])

            if good_bodies and small_shadows:
                df.loc[i, 'three_white_soldiers'] = 1.0

        # Three Black Crows
        bearish_candles = all(
            [df.loc[i-j, 'close'] < df.loc[i-j, 'open'] for j in range(3)])
        lower_closes = df.loc[i, 'close'] < df.loc[i -
                                                   1, 'close'] < df.loc[i-2, 'close']
        lower_opens = df.loc[i, 'open'] < df.loc[i -
                                                 1, 'open'] < df.loc[i-2, 'open']

        if bearish_candles and lower_closes and lower_opens:
            # Check for substantial bodies with small lower shadows
            bodies = [abs(df.loc[i-j, 'close'] - df.loc[i-j, 'open'])
                      for j in range(3)]
            ranges = [df.loc[i-j, 'high'] - df.loc[i-j, 'low']
                      for j in range(3)]
            lower_shadows = [min(
                df.loc[i-j, 'open'], df.loc[i-j, 'close']) - df.loc[i-j, 'low'] for j in range(3)]

            good_bodies = all([bodies[j] / ranges[j] > 0.5 for j in range(3)])
            small_shadows = all(
                [lower_shadows[j] / bodies[j] < 0.3 for j in range(3)])

            if good_bodies and small_shadows:
                df.loc[i, 'three_black_crows'] = 1.0

    return df


def add_advanced_features(df):
    """Add more advanced features to improve prediction accuracy"""
    # Price action features
    df['price_momentum'] = df['close'].pct_change(5)
    df['price_acceleration'] = df['price_momentum'].diff()

    # Volume profile
    df['relative_volume'] = df['volume'] / df['volume'].rolling(20).mean()
    df['volume_delta'] = df['volume'].diff()

    # Volatility features
    df['volatility'] = df['close'].rolling(14).std() / df['close']

    # Market regime features
    df['bull_market'] = (
        df['close'] > df['close'].rolling(50).mean()).astype(float)
    df['bear_market'] = (
        df['close'] < df['close'].rolling(50).mean()).astype(float)

    # Range features
    df['daily_range'] = (df['high'] - df['low']) / df['close']

    # Advanced candlestick features
    df['body_to_range'] = abs(df['close'] - df['open']
                              ) / (df['high'] - df['low'])
    df['upper_shadow_ratio'] = (
        df['high'] - df[['open', 'close']].max(axis=1)) / (df['high'] - df['low'] + 0.00001)
    df['lower_shadow_ratio'] = (df[['open', 'close']].min(
        axis=1) - df['low']) / (df['high'] - df['low'] + 0.00001)

    return df


def calculate_indicators(df):
    """Calculate technical indicators"""
    try:
        # First, make sure the DataFrame has a unique index
        df = df.reset_index(drop=True)

        # Calculate RSI (14)
        delta = df['close'].diff()
        gain = delta.where(delta > 0, 0).rolling(window=14).mean()
        loss = -delta.where(delta < 0, 0).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))

        # Calculate MACD (12, 26, 9)
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']

        # Calculate Bollinger Bands (20, 2)
        df['sma20'] = df['close'].rolling(window=20).mean()
        df['stddev'] = df['close'].rolling(window=20).std()
        df['bb_upper'] = df['sma20'] + (df['stddev'] * 2)
        df['bb_lower'] = df['sma20'] - (df['stddev'] * 2)
        df['bb_width'] = (df['bb_upper'] - df['bb_lower']) / df['sma20']
        df['bb_pct'] = (df['close'] - df['bb_lower']) / \
            (df['bb_upper'] - df['bb_lower'])

        # Calculate ATR (14)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['atr'] = true_range.rolling(14).mean()

        # Volume indicators
        df['volume_sma_20'] = df['volume'].rolling(window=20).mean()

        # Calculate EMAs
        df['ema9'] = df['close'].ewm(span=9, adjust=False).mean()
        df['ema21'] = df['close'].ewm(span=21, adjust=False).mean()
        df['ema50'] = df['close'].ewm(span=50, adjust=False).mean()
        df['ema_cross'] = (df['ema9'] > df['ema21']).astype(float)

        # Calculate candlestick patterns
        try:
            df = calculate_candlestick_patterns(df)
        except Exception as e:
            logger.error(f"Error calculating candlestick patterns: {str(e)}")
            # Add empty pattern columns if they failed
            pattern_columns = [
                'bullish_engulfing', 'bearish_engulfing', 'doji',
                'hammer', 'shooting_star', 'three_white_soldiers', 'three_black_crows'
            ]
            for col in pattern_columns:
                df[col] = 0.0

        # Add advanced features
        df = add_advanced_features(df)

        return df

    except Exception as e:
        logger.error(f"Error calculating indicators: {str(e)}")
        logger.error(traceback.format_exc())
        return df


def prepare_features(df):
    """Prepare features and target for ML model"""
    try:
        # Calculate indicators
        df = calculate_indicators(df)

        # Drop rows with NaN values
        df = df.dropna()

        # Select features (including candlestick patterns and advanced features)
        features = [
            # Technical indicators
            'rsi', 'macd', 'macd_signal', 'macd_hist', 'bb_upper', 'bb_lower',
            'bb_width', 'bb_pct', 'atr', 'volume', 'volume_sma_20',
            'ema9', 'ema21', 'ema50', 'ema_cross',
            # Candlestick patterns
            'bullish_engulfing', 'bearish_engulfing', 'doji',
            'hammer', 'shooting_star', 'three_white_soldiers', 'three_black_crows',
            # Advanced features
            'price_momentum', 'price_acceleration', 'relative_volume',
            'volume_delta', 'volatility', 'bull_market', 'bear_market',
            'daily_range', 'body_to_range', 'upper_shadow_ratio', 'lower_shadow_ratio'
        ]

        X = df[features]
        y = df['target']

        return X, y

    except Exception as e:
        logger.error(f"Error preparing features: {str(e)}")
        logger.error(traceback.format_exc())
        return None, None


def select_important_features(X, y, threshold=0.01):
    """Select most important features based on importance"""
    model = RandomForestClassifier(n_estimators=100, random_state=42)
    model.fit(X, y)

    # Get feature importance
    importances = model.feature_importances_

    # Create DataFrame of feature importances
    feature_importance = pd.DataFrame({
        'feature': X.columns,
        'importance': importances
    }).sort_values('importance', ascending=False)

    logger.info("Feature importance:")
    logger.info(feature_importance)

    # Select features above threshold
    selected_features = feature_importance[
        feature_importance['importance'] > threshold
    ]['feature'].tolist()

    logger.info(
        f"Selected {len(selected_features)} features out of {X.shape[1]}")

    return X[selected_features], selected_features


def train_model():
    """Train and save the Random Forest model"""
    try:
        # Fetch data
        logger.info("Fetching training data...")
        data = fetch_training_data()

        if data is None or data.empty:
            logger.error("No data available for training")
            return False

        # Prepare features
        logger.info(
            "Preparing features with candlestick patterns and advanced features...")
        X, y = prepare_features(data)

        if X is None or y is None:
            logger.error("Failed to prepare features")
            return False

        # Select important features
        logger.info("Selecting important features...")
        X, selected_features = select_important_features(X, y)

        # Time-series split for validation
        logger.info("Setting up time-series cross-validation...")
        tscv = TimeSeriesSplit(n_splits=5)

        total_acc = 0
        fold = 1

        # Cross-validation
        for train_index, test_index in tscv.split(X):
            logger.info(f"Training fold {fold}...")
            X_train, X_test = X.iloc[train_index], X.iloc[test_index]
            y_train, y_test = y.iloc[train_index], y.iloc[test_index]

            # Train model for this fold
            model = RandomForestClassifier(
                n_estimators=200,  # Increased from 100
                max_depth=15,      # Added depth limit
                min_samples_split=5,
                min_samples_leaf=2,
                random_state=42,
                class_weight='balanced'
            )

            model.fit(X_train, y_train)

            # Evaluate
            y_pred = model.predict(X_test)
            acc = accuracy_score(y_test, y_pred)

            logger.info(f"Fold {fold} accuracy: {acc:.4f}")
            total_acc += acc
            fold += 1

        # Final model on all data
        logger.info("Training final model on all data...")
        final_model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            class_weight='balanced'
        )
        final_model.fit(X, y)

        # Log average cross-validation accuracy
        avg_acc = total_acc / (fold - 1)
        logger.info(f"Average CV accuracy: {avg_acc:.4f}")

        # Print feature importance
        feature_importance = pd.DataFrame({
            'feature': X.columns,
            'importance': final_model.feature_importances_
        }).sort_values(by='importance', ascending=False)

        logger.info("\nFinal Feature Importance:")
        logger.info(feature_importance)

        # Save model
        model_path = os.path.join('models', 'random_forest_model.joblib')
        joblib.dump(final_model, model_path)
        logger.info(f"Model saved to {model_path}")

        # Also save feature info
        feature_info = {
            'feature_names': list(X.columns),
            'trained_date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'cv_accuracy': avg_acc,
            'pattern_features': ['bullish_engulfing', 'bearish_engulfing', 'doji',
                                 'hammer', 'shooting_star', 'three_white_soldiers', 'three_black_crows'],
            'advanced_features': [
                'price_momentum', 'price_acceleration', 'relative_volume',
                'volume_delta', 'volatility', 'bull_market', 'bear_market',
                'daily_range', 'body_to_range', 'upper_shadow_ratio', 'lower_shadow_ratio'
            ]
        }

        feature_path = os.path.join('models', 'feature_info.joblib')
        joblib.dump(feature_info, feature_path)
        logger.info(f"Feature info saved to {feature_path}")

        return True

    except Exception as e:
        logger.error(f"Error training model: {str(e)}")
        logger.error(traceback.format_exc())
        return False


if __name__ == "__main__":
    logger.info("Starting enhanced ML model training with advanced features...")
    success = train_model()

    if success:
        logger.info("Training completed successfully")
    else:
        logger.error("Training failed")
