import pandas as pd
import numpy as np
import ta

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    # Price Change %
    df['returns'] = df['close'].pct_change()

    # RSI
    df['rsi'] = ta.momentum.RSIIndicator(close=df['close'], window=14).rsi()

    # MACD
    macd = ta.trend.MACD(close=df['close'])
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()

    # EMA 20 / 50 / 100 / 200
    df['ema20'] = ta.trend.EMAIndicator(close=df['close'], window=20).ema_indicator()
    df['ema50'] = ta.trend.EMAIndicator(close=df['close'], window=50).ema_indicator()
    df['ema100'] = ta.trend.EMAIndicator(close=df['close'], window=100).ema_indicator()
    df['ema200'] = ta.trend.EMAIndicator(close=df['close'], window=200).ema_indicator()

    # Bollinger Bands
    bb = ta.volatility.BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_upper'] = bb.bollinger_hband()
    df['bb_lower'] = bb.bollinger_lband()

    # Stochastic RSI
    stoch = ta.momentum.StochRSIIndicator(close=df['close'], window=14)
    df['stoch_k'] = stoch.stochrsi_k()
    df['stoch_d'] = stoch.stochrsi_d()

    # MFI
    df['mfi'] = ta.volume.MFIIndicator(high=df['high'], low=df['low'], close=df['close'], volume=df['volume']).money_flow_index()

    # CCI
    df['cci'] = ta.trend.CCIIndicator(high=df['high'], low=df['low'], close=df['close'], window=20).cci()

    # ADX
    df['adx'] = ta.trend.ADXIndicator(high=df['high'], low=df['low'], close=df['close'], window=14).adx()

    # ATR
    df['atr'] = ta.volatility.AverageTrueRange(high=df['high'], low=df['low'], close=df['close']).average_true_range()

    # OBV
    df['obv'] = ta.volume.OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()

    # VWAP (manual)
    df['vwap'] = (df['volume'] * (df['high'] + df['low'] + df['close']) / 3).cumsum() / df['volume'].cumsum()

    # Trend & Confidence Logic
    df['direction'] = 'none'
    df['confidence'] = 0.0
    df['tp1_chance'] = 0.0

    for i in range(len(df)):
        score = 0
        tp_score = 0

        # Price above EMA
        if df['close'].iloc[i] > df['ema20'].iloc[i]: score += 1
        if df['close'].iloc[i] > df['ema50'].iloc[i]: score += 1
        if df['close'].iloc[i] > df['ema100'].iloc[i]: score += 1
        if df['close'].iloc[i] > df['ema200'].iloc[i]: score += 1

        # RSI bullish
        if df['rsi'].iloc[i] > 50: score += 1
        if df['rsi'].iloc[i] < 30: score -= 1

        # MACD
        if df['macd'].iloc[i] > df['macd_signal'].iloc[i]: score += 1
        else: score -= 1

        # MFI
        if df['mfi'].iloc[i] > 50: score += 1
        if df['mfi'].iloc[i] < 20: score -= 1

        # Stochastic
        if df['stoch_k'].iloc[i] > df['stoch_d'].iloc[i]: score += 1

        # CCI
        if df['cci'].iloc[i] > 100: score += 1
        if df['cci'].iloc[i] < -100: score -= 1

        # ADX strong trend
        if df['adx'].iloc[i] > 20: score += 1

        # Bollinger logic
        if df['close'].iloc[i] < df['bb_lower'].iloc[i]: tp_score += 1
        if df['close'].iloc[i] > df['bb_upper'].iloc[i]: tp_score += 1

        # Final assignment
        direction = 'LONG' if score >= 5 else 'SHORT' if score <= -5 else 'none'
        confidence = round(abs(score) / 10 * 100, 2)
        tp1_possibility = round(tp_score / 2, 2)

        df.at[df.index[i], 'direction'] = direction
        df.at[df.index[i], 'confidence'] = confidence
        df.at[df.index[i], 'tp1_chance'] = tp1_possibility

    return df
