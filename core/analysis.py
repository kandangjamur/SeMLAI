# Analyze single symbol across timeframes
def analyze_symbol(symbol):
    try:
        final_signals = []
        print(f"Analyzing {symbol} for signals...")  # Print at the beginning of analysis

        for tf_label, interval in TIMEFRAMES.items():
            df = fetch_ohlcv(symbol, interval)
            if df is None or len(df) < 20:
                continue

            indicators = calculate_indicators(df)
            score, confidence, reasons = score_signal(indicators)

            # Print technical indicators after calculation
            print(f"RSI: {indicators['rsi'].iloc[-1]}, MACD: {indicators['macd'].iloc[-1]}, EMA: {indicators['ema_12'].iloc[-1]}, Volume: {indicators['volume_change'].iloc[-1]}")

            # Print signal after scoring
            print(f"Signal for {symbol}: {tf_label} - Score: {score}, Confidence: {confidence}%")

            if score >= 4:  # Triple verification threshold
                final_signals.append({
                    'symbol': symbol,
                    'timeframe': tf_label,
                    'score': score,
                    'confidence': confidence,
                    'reasons': reasons,
                    'price': df['close'].iloc[-1]
                })

        return final_signals

    except Exception as e:
        log(f"Error in analyze_symbol for {symbol}: {e}")
        return []

# Score signal based on multiple hedge-fund level indicators
def score_signal(indicators):
    score = 0
    conditions = []

    # RSI condition
    if indicators['rsi'].iloc[-1] < 30:
        score += 1
        conditions.append('RSI oversold')

    # MACD crossover
    if indicators['macd'].iloc[-1] > indicators['macd_signal'].iloc[-1]:
        score += 1
        conditions.append('MACD bullish crossover')

    # EMA crossover
    if indicators['ema_12'].iloc[-1] > indicators['ema_26'].iloc[-1]:
        score += 1
        conditions.append('EMA 12 > EMA 26')

    # Volume spike (100%+ change)
    if indicators['volume_change'].iloc[-1] > 50:
        score += 1
        conditions.append('Volume spike detected')

    # Bollinger Band lower touch (buy signal)
    if indicators['close'].iloc[-1] < indicators['bb_lower'].iloc[-1]:
        score += 1
        conditions.append('Bollinger lower band touch')

    # ATR rising = increasing volatility
    if indicators['atr'].iloc[-1] > indicators['atr'].iloc[-2]:
        score += 1
        conditions.append('ATR rising')

    confidence = round((score / 6) * 100, 2)
    return score, confidence, conditions
