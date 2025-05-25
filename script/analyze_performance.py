import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# Configure plot style
plt.style.use('ggplot')
sns.set_theme()


def analyze_signal_performance():
    """Analyze signal performance from the signal_performance.csv file"""
    # Load the data
    try:
        df = pd.read_csv('logs/signal_performance.csv')
        print(f"Loaded {len(df)} signals for analysis")
    except Exception as e:
        print(f"Error loading signal data: {e}")
        return

    # Convert hit_time to datetime
    df['hit_time'] = pd.to_datetime(df['hit_time'], errors='coerce')
    df['timestamp'] = pd.to_datetime(df['timestamp'])

    # Create completed signals dataframe
    completed = df[df['status'] != 'pending'].copy()
    pending = df[df['status'] == 'pending']

    print(f"Completed signals: {len(completed)}")
    print(f"Pending signals: {len(pending)}")

    if len(completed) == 0:
        print("No completed signals to analyze.")
        return

    # Performance metrics
    success_rate = (completed['success'] == 'YES').mean() * 100
    avg_profit = completed[completed['success'] == 'YES']['profit_loss'].mean()
    avg_loss = completed[completed['success'] == 'NO']['profit_loss'].mean()
    avg_duration = completed['duration_minutes'].mean()

    print(f"Success rate: {success_rate:.2f}%")
    print(f"Average profit: {avg_profit:.2f}%")
    print(f"Average loss: {avg_loss:.2f}%")
    print(f"Average trade duration: {avg_duration:.2f} minutes")

    # Hit rates by target
    tp1_hits = (completed['status'] == 'tp1').sum()
    tp2_hits = (completed['status'] == 'tp2').sum()
    tp3_hits = (completed['status'] == 'tp3').sum()
    sl_hits = (completed['status'] == 'sl').sum()

    print(f"TP1 hits: {tp1_hits} ({tp1_hits/len(completed)*100:.2f}%)")
    print(f"TP2 hits: {tp2_hits} ({tp2_hits/len(completed)*100:.2f}%)")
    print(f"TP3 hits: {tp3_hits} ({tp3_hits/len(completed)*100:.2f}%)")
    print(f"SL hits: {sl_hits} ({sl_hits/len(completed)*100:.2f}%)")

    # Performance by timeframe
    print("\nPerformance by timeframe:")
    timeframe_performance = completed.groupby('timeframe').agg({
        'profit_loss': 'mean',
        'success': lambda x: (x == 'YES').mean() * 100
    }).sort_values('success', ascending=False)
    print(timeframe_performance)

    # Performance by direction
    print("\nPerformance by direction:")
    direction_performance = completed.groupby('direction').agg({
        'profit_loss': 'mean',
        'success': lambda x: (x == 'YES').mean() * 100
    })
    print(direction_performance)

    # Profit distribution
    plt.figure(figsize=(10, 6))
    sns.histplot(completed['profit_loss'], bins=20)
    plt.title('Profit/Loss Distribution')
    plt.xlabel('Profit/Loss %')
    plt.ylabel('Count')
    plt.axvline(x=0, color='r', linestyle='--')

    # Save the plot
    plt.tight_layout()
    plt.savefig('logs/profit_distribution.png')

    # Success by symbol
    symbol_performance = completed.groupby('symbol').agg({
        'profit_loss': 'mean',
        'success': lambda x: (x == 'YES').mean() * 100,
        'symbol': 'count'
    }).rename(columns={'symbol': 'count'})

    # Filter symbols with enough trades
    symbol_performance = symbol_performance[symbol_performance['count'] >= 2]

    # Sort by success rate
    symbol_performance = symbol_performance.sort_values(
        'success', ascending=False)

    # Top 10 symbols by success rate
    plt.figure(figsize=(12, 6))
    top_symbols = symbol_performance.head(10)
    sns.barplot(x=top_symbols.index, y='success', data=top_symbols)
    plt.title('Top 10 Symbols by Success Rate')
    plt.xlabel('Symbol')
    plt.ylabel('Success Rate %')
    plt.xticks(rotation=45)

    # Save the plot
    plt.tight_layout()
    plt.savefig('logs/top_symbols.png')

    print("\nAnalysis complete. Check the logs directory for visualizations.")


if __name__ == "__main__":
    analyze_signal_performance()
