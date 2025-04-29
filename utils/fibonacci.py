# utils/fibonacci.py
def calculate_fibonacci_levels(price, direction="LONG"):
    levels = {}
    if direction == "LONG":
        levels["tp1"] = price * 1.012
        levels["tp2"] = price * 1.018
        levels["tp3"] = price * 1.025
    else:
        levels["tp1"] = price * 0.988
        levels["tp2"] = price * 0.982
        levels["tp3"] = price * 0.975
    return levels
