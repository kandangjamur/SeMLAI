def whale_check(symbol, exchange):
    try:
        book = exchange.fetch_order_book(symbol)
        bid_vol = sum([b[1] for b in book['bids'][:10]])
        ask_vol = sum([a[1] for a in book['asks'][:10]])
        imbalance = abs(bid_vol - ask_vol) / max(bid_vol, ask_vol)
        return imbalance > 0.2
    except:
        return False
