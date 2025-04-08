import pandas as pd
import ta

def compute_indicators(df):
    """
    Calculate all key indicators on the provided DataFrame.
    Expected columns: ['open', 'high', 'low', 'close', 'volume']
    """
    df = df.copy()

    # RSI
    df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()

    # MACD
    macd = ta.trend.MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff()

    # EMA (Exponential Moving Averages)
    df['ema_9'] = ta.trend.EMAIndicator(close=df['close'], window=9).ema_indicator()
    df['ema_20'] = ta.trend.EMAIndicator(close=df['close'], window=20).ema_indicator()
    df['ema_50'] = ta.trend.EMAIndicator(close=df['close'], window=50).ema_indicator()
    df['ema_100'] = ta.trend.EMAIndicator(close=df['close'], window=100).ema_indicator()

    # SMA (Simple Moving Average)
    df['sma_50'] = ta.trend.SMAIndicator(close=df['close'], window=50).sma_indicator()
    df['sma_200'] = ta.trend.SMAIndicator(close=df['close'], window=200).sma_indicator()

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_middle'] = bb.bollinger_mavg()
    df['bb_lower'] = bb.bollinger_lband()
    df['bb_width'] = df['bb_upper'] - df['bb_lower']

    # Average True Range (ATR)
    df['atr'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close'], window=14).average_true_range()

    # Stochastic Oscillator
    stoch = ta.momentum.StochasticOscillator(high=df['high'], low=df['low'], close=df['close'], window=14, smooth_window=3)
    df['stoch_k'] = stoch.stoch()
    df['stoch_d'] = stoch.stoch_signal()

    # CCI (Commodity Channel Index)
    df['cci'] = ta.trend.CCIIndicator(high=df['high'], low=df['low'], close=df['close'], window=20).cci()

    # OBV (On-Balance Volume)
    df['obv'] = ta.volume.OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()

    # MFI (Money Flow Index)
    df['mfi'] = ta.volume.MFIIndicator(high=df['high'], low=df['low'], close=df['close'], volume=df['volume'], window=14).money_flow_index()

    # ROC (Rate of Change)
    df['roc'] = ta.momentum.ROCIndicator(close=df['close'], window=12).roc()

    # VWAP (Volume Weighted Average Price)
    df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()

    return df
