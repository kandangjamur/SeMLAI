def analyze_symbol(symbol):
    try:
        final_signals = []
        print(f"\n[🔍] Analyzing {symbol} for signals...")

        for tf_label, interval in TIMEFRAMES.items():
            df = fetch_ohlcv(symbol, interval)
            if df is None or len(df) < 20:
                print(f"[⚠️] Skipping {symbol} - Not enough data for {tf_label}")
                continue

            indicators = calculate_indicators(df)
            score, confidence, reasons = score_signal(indicators)

            # Safe printing of indicators
            try:
                rsi = indicators['rsi'].iloc[-1]
                macd = indicators['macd'].iloc[-1]
                ema = indicators['ema_12'].iloc[-1]
                vol = indicators['volume_change'].iloc[-1]
                print(f"[📊] {symbol} ({tf_label}) → RSI: {rsi:.2f}, MACD: {macd:.2f}, EMA: {ema:.2f}, Volume Change: {vol:.2f}%")
            except Exception as e:
                print(f"[⚠️] Error printing indicators for {symbol} ({tf_label}): {e}")

            # Safe printing of signal info
            try:
                print(f"[📈] Signal for {symbol} ({tf_label}) → Score: {score}, Confidence: {confidence}%")
            except Exception as e:
                print(f"[⚠️] Error printing signal for {symbol} ({tf_label}): {e}")

            if score >= 4:
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
        log(f"[🔥 ERROR] analyze_symbol failed for {symbol}: {e}")
        return []
