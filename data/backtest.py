import pandas as pd
from utils.logger import log

def get_tp1_hit_rate(symbol: str, timeframe: str, backtest_file: str = "data/backtest_data.csv") -> float:
    """
    بیک ٹیسٹ فائل سے سمبل اور ٹائم فریم کے لیے TP1 ہٹ ریٹ کیلکولیٹ کرتا ہے۔
    
    Args:
        symbol (str): سمبل (مثلاً BTC/USDT)
        timeframe (str): ٹائم فریم (مثلاً 15m, 1h, 4h)
        backtest_file (str): بیک ٹیسٹ فائل کا پاتھ
    
    Returns:
        float: TP1 ہٹ ریٹ (0 سے 1 کے درمیان)
    """
    try:
        # بیک ٹیسٹ ڈیٹا پڑھو
        df = pd.read_csv(backtest_file)
        
        # سمبل اور ٹائم فریم کے لیے فلٹر کرو
        filtered_df = df[(df["symbol"] == symbol) & (df["timeframe"] == timeframe)]
        
        if len(filtered_df) < 10:
            log(f"[{symbol}] Insufficient backtest data for {timeframe}: {len(filtered_df)} trades", level="WARNING")
            return 0.7  # ڈیفالٹ ہٹ ریٹ
        
        # TP1 ہٹ ریٹ کیلکولیٹ کرو
        hit_rate = filtered_df["hit_tp1"].mean()
        
        if pd.isna(hit_rate):
            log(f"[{symbol}] No valid TP1 hit data for {timeframe}", level="WARNING")
            return 0.7  # ڈیفالٹ ہٹ ریٹ
        
        log(f"[{symbol}] TP1 hit rate for {timeframe}: {hit_rate:.2%}")
        return hit_rate
    
    except FileNotFoundError:
        log(f"Backtest file {backtest_file} not found", level="ERROR")
        return 0.7  # ڈیفالٹ ہٹ ریٹ
    except Exception as e:
        log(f"Error calculating TP1 hit rate for {symbol}: {str(e)}", level="ERROR")
        return 0.7  # ڈیفالٹ ہٹ ریٹ
