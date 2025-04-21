def calculate_fibonacci_levels(price, direction="LONG"):
    """
    Calculates Fibonacci retracement or extension levels based on price and direction.
    Commonly used levels: 0.236, 0.382, 0.5, 0.618, 0.786, 1.618
    """
    levels = {}

    if direction == "LONG":
        levels["fib_0.236"] = round(price * 1.236, 4)
        levels["fib_0.382"] = round(price * 1.382, 4)
        levels["fib_0.5"] = round(price * 1.5, 4)
        levels["fib_0.618"] = round(price * 1.618, 4)
        levels["fib_0.786"] = round(price * 1.786, 4)
    else:  # SHORT
        levels["fib_0.236"] = round(price * 0.764, 4)
        levels["fib_0.382"] = round(price * 0.618, 4)
        levels["fib_0.5"] = round(price * 0.5, 4)
        levels["fib_0.618"] = round(price * 0.382, 4)
        levels["fib_0.786"] = round(price * 0.214, 4)

    return levels
