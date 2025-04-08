def classify_trade(rsi, macd, ema, whale_activity, news_impact):
    if rsi < 30 and macd[0] > macd[1] and whale_activity:
        return "scalping"
    elif rsi > 70 and macd[0] < macd[1] and news_impact == '🔴 Negative':
        return "normal"
    elif whale_activity:
        return "spot"
    return "normal"
