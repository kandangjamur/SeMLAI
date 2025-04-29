def calculate_fibonacci_levels(price, direction="LONG"):
    if direction == "LONG":
        return {
            "tp1": price * 1.012,
            "tp2": price * 1.018,
            "tp3": price * 1.025
        }
    else:
        return {
            "tp1": price * 0.988,
            "tp2": price * 0.982,
            "tp3": price * 0.975
        }
