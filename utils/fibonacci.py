def calculate_fibonacci_levels(price, direction="LONG"):
    levels = {}
    if direction == "LONG":
        levels["tp1"] = price * 1.02
        levels["tp2"] = price * 1.04
        levels["tp3"] = price * 1.08
    else:
        levels["tp1"] = price * 0.98
        levels["tp2"] = price * 0.96
        levels["tp3"] = price * 0.92
    return levels
