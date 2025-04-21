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

# Download BTC/USDT-like data
ohlcv = []
limit = 1000
init_date = pd.Timestamp("2017-01-01")
today = pd.Timestamp.today()
exchange = ccxt.binance()
while init_date < today:
    ohlcv += exchange.fetch_ohlcv('BTC/USDT', since=init_date.value // 10**6, limit=limit, timeframe='1h')
    init_date += pd.Timedelta(1000, "h")

# DataFrame setup
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']).drop_duplicates()
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
        print(f"[ENTRY] {entry_time} @ {entry_price:.2f}")

    # Exit condition
    elif position:
        price = row["close"]
        stop_hit = price <= stop_loss_price
        cross_down = row["close"] > row["DEMA"] and row["TEMA_FAST"] < row["TEMA_SLOW"] < prev["TEMA_FAST"]

        if stop_hit or cross_down:
            sell_balance = units * price
            position = False
            exit_time = row.name
            print(f"[EXIT] {exit_time} @ {price:.2f}")
            trades.append({
                "entry_time": entry_time,
                "exit_time": exit_time,
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

    # Performance Metrics
    wins = trade_df[trade_df['pnl'] > 0]
    losses = trade_df[trade_df['pnl'] <= 0]
    win_rate = len(wins) / len(trade_df) * 100
    profit_factor = wins['pnl'].sum() / abs(losses['pnl'].sum()) if not losses.empty else float('inf')

    print("\nStats:")
    print(f"Total Trades: {len(trade_df)}")
    print(f"Win Trades: {len(wins)}")
    print(f"Lose Trades: {len(losses)}")
    print(f"Win Rate: {win_rate:.2f}%")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Total PnL: ${trade_df['pnl'].sum():.2f}")

    # Plot
    plt.figure(figsize=(12, 5))
    plt.plot(df["close"], label="Close Price")
    for trade in trades:
        plt.axvline(trade["entry_time"], color="blue", linestyle="--", alpha=0.7)
        plt.axvline(trade["exit_time"], color="red", linestyle="--", alpha=0.7)
    plt.title("EMA Strategy Backtest with pandas-ta")
    plt.legend()
    plt.grid()
    plt.tight_layout()
    plt.savefig("ema_strategy")