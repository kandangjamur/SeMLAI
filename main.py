# core/analysis.py میں analyze_symbol فنکشن کے اندر تبدیلی
async def analyze_symbol(symbol: str, exchange, predictor, timeframe: str = "15m"):
    # ... (پچھلا کوڈ وہی رہے گا تاکہ OHLCV اور انڈیکیٹرز کیلکولیشن ہو)

    # Set dynamic TP hit rates based on predictor confidence
    signal = await predictor.predict_signal(symbol, df, timeframe)
    if signal is None:
        log(f"[{symbol}] No valid signal from predictor", level="INFO")
        # Check for breakout as fallback
        breakout = detect_breakout(symbol, df)
        if breakout["is_breakout"]:
            direction = "LONG" if breakout["direction"] == "up" else "SHORT"
            confidence = 90.0  # Fixed confidence for breakout
            tp1_possibility = 0.85
            tp2_possibility = 0.65
            tp3_possibility = 0.45
        else:
            return None
    else:
        direction = signal["direction"]
        confidence = signal["confidence"]
        # Dynamic TP possibilities based on confidence (threshold raised to 75%)
        tp1_possibility = min(0.80 + (confidence / 100 - 0.75) * 0.15, 0.95)
        tp2_possibility = min(0.60 + (confidence / 100 - 0.75) * 0.20, 0.80)
        tp3_possibility = min(0.40 + (confidence / 100 - 0.75) * 0.25, 0.65)
        # Skip if confidence is too low
        if confidence < 75.0:
            log(f"[{symbol}] Low confidence: {confidence:.2f}%", level="INFO")
            return None

    # ... (باقی کوڈ وہی رہے گا، جیسے TP/SL کیلکولیشن اور ریزلٹ بنانا)
