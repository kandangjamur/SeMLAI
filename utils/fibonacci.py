def calculate_fibonacci_levels(price, direction="LONG"):
    levels = {
        "tp1": price * 1.015 if direction == "LONG" else price * 0.985,
        "tp2": price * 1.025 if direction == "LONG" else price * 0.975,
        "tp3": price * 1.035 if direction == "LONG" else price * 0.965,
    }
    return levels
