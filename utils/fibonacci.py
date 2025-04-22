def calculate_fibonacci_levels(price, direction="LONG"):
    """
    Calculates Fibonacci levels for TP targets.
    For LONG trades, returns TP levels as extensions:
      - fib_tp1 = price * 1.236
      - fib_tp2 = price * 1.382
      - fib_tp3 = price * 1.618
    For SHORT trades, returns adjusted levels.
    """
    if direction == "LONG":
        return {
            "tp1": round(price * 1.236, 3),
            "tp2": round(price * 1.382, 3),
            "tp3": round(price * 1.618, 3)
        }
    else:
        return {
            "tp1": round(price * 0.764, 3),
            "tp2": round(price * 0.618, 3),
            "tp3": round(price * 0.382, 3)
        }
