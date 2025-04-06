def format_signal(data):
    return f"""🎯 **ELITE SIGNAL** (Confidence: {data['confidence']})
━━━━━━━━━━━━━━━━━━━
📈 Coin: **{data['symbol']}**
📉 Type: **{data['side']} {'🟢' if data['side']=='BUY' else '🔴'}**
💵 Entry: `${data['entry']}`

🎯 Targets:
• TP1 → `${data['tp1']}`
• TP2 → `${data['tp2']}`

🛡️ Stop Loss: `${data['sl']}`
📊 Volume Spike: `{data['volume_spike']}x`
🐋 Whale Activity: {'✅ Detected' if data['whale_activity'] else '❌ None'}
📰 News Impact: {data['news_impact']}

📌 Sentiment: {data['sentiment']} | Trend Strength: {data['trend_strength']}
🕐 Timeframe: {data['timeframe']} → {data['recommendation']}
📌 Trade Type: **{data['trade_type']}**
📌 Leverage: **{data['leverage']}x**
━━━━━━━━━━━━━━━━━━━
#{data['signal_tag']} | #{data['symbol']} #Binance
"""
