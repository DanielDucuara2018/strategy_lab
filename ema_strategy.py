import pandas as pd
import ccxt
import pandas_ta as ta
import matplotlib.pyplot as plt

# Parameters
TEMA_FAST = 10
TEMA_SLOW = 50
DEMA_PERIOD = 200
STOP_LOSS_PCT = 0.05  # 5%
INITIAL_BALANCE = 2000

# Download BTC/USDT-like data (close approximation using BTC-USD)
exchange = ccxt.binance()
ohlcv = exchange.fetch_ohlcv('BTC/USDT', since=int(pd.Timestamp("2021-01-01").timestamp()), limit=1500, timeframe='1h')
# DataFrame setup
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# Compute indicators using pandas-ta
df["DEMA"] = ta.dema(df["close"], length=DEMA_PERIOD)
df["TEMA_FAST"] = ta.tema(df["close"], length=TEMA_FAST)
df["TEMA_SLOW"] = ta.tema(df["close"], length=TEMA_SLOW)

# Backtest logic
position = False
entry_price = 0
balance = INITIAL_BALANCE
units = 0
trades = []

for i in range(1, len(df)):
    row = df.iloc[i]
    prev = df.iloc[i - 1]

    # Entry condition
    if not position and row["close"] > row["DEMA"] and prev["TEMA_FAST"] < prev["TEMA_SLOW"] and row["TEMA_FAST"] > row["TEMA_SLOW"]:
        entry_price = row["close"]
        stop_loss_price = entry_price * (1 - STOP_LOSS_PCT)
        units = balance / entry_price
        position = True
        entry_time = row.name
        print(f"Buy at {entry_time} price: {entry_price:.2f}")

    # Exit condition
    elif position:
        price = row["close"]
        stop_hit = price <= stop_loss_price
        cross_down = row["close"] > row["DEMA"] and row["TEMA_FAST"] < row["TEMA_SLOW"] < prev["TEMA_FAST"]

        if stop_hit or cross_down:
            sell_balance = units * price
            position = False
            exit_time = row.name
            print(f"Sell at {exit_time} price: {price:.2f}")
            trades.append({
                "entry": entry_time,
                "exit": exit_time,
                "entry_price": entry_price,
                "exit_price": price,
                "pnl": sell_balance - balance,
                "old_balance": balance,
                "new_balance": sell_balance
            })
            balance = sell_balance

# Show final results
print(f"\nFinal balance: ${balance:.2f}")
if trades:
    trade_df = pd.DataFrame(trades)
    print("\nTrade Summary:")
    print(trade_df)

    # Plot
    plt.figure(figsize=(12, 5))
    plt.plot(df["close"], label="Close Price")
    for trade in trades:
        plt.axvline(trade["entry"], color="blue", linestyle="--", alpha=0.7)
        plt.axvline(trade["exit"], color="red", linestyle="--", alpha=0.7)
    plt.title("EMA Strategy Backtest with pandas-ta")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.savefig("ema_strategy")