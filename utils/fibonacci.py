import pandas as pd
from utils.logger import log

def calculate_fibonacci_levels(price, direction="LONG", atr=0.01):
    try:
        if price <= 0 or atr <= 0:
            log(f"Invalid price or ATR: price={price}, atr={atr}", level='ERROR')
            return {"tp1": None, "tp2": None, "tp3": None}

        # Fibonacci ratios
        fib_ratios = {"tp1": 0.382, "tp2": 0.618, "tp3": 1.0}
        levels = {}

        # Adjust levels based on direction
        if direction == "LONG":
            levels["tp1"] = price + atr * fib_ratios["tp1"] * 2
            levels["tp2"] = price + atr * fib_ratios["tp2"] * 3
            levels["tp3"] = price + atr * fib_ratios["tp3"] * 4
        else:  # SHORT
            levels["tp1"] = price - atr * fib_ratios["tp1"] * 2
            levels["tp2"] = price - atr * fib_ratios["tp2"] * 3
            levels["tp3"] = price - atr * fib_ratios["tp3"] * 4

        # Calculate dynamic possibilities
        volatility_factor = atr / price
        levels["tp1_possibility"] = min(95, 85 - (abs(levels["tp1"] - price) / price * 100) + (5 if volatility_factor < 0.02 else 0))
        levels["tp2_possibility"] = min(85, 75 - (abs(levels["tp2"] - price) / price * 100) - (5 if volatility_factor < 0.02 else 10))
        levels["tp3_possibility"] = min(75, 65 - (abs(levels["tp3"] - price) / price * 100) - (15 if volatility_factor < 0.02 else 20))

        # Round and validate
        for key in ["tp1", "tp2", "tp3"]:
            if levels[key] <= 0:
                log(f"Invalid Fibonacci level: {key}={levels[key]}", level='ERROR')
                return {"tp1": None, "tp2": None, "tp3": None}
            levels[key] = round(levels[key], 4)

        levels["tp1_possibility"] = round(levels["tp1_possibility"], 2)
        levels["tp2_possibility"] = round(levels["tp2_possibility"], 2)
        levels["tp3_possibility"] = round(levels["tp3_possibility"], 2)

        return levels

    except Exception as e:
        log(f"Error in calculate_fibonacci_levels: {e}", level='ERROR')
        return {"tp1": None, "tp2": None, "tp3": None}
