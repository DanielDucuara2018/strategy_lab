import pandas as pd
import pandas_ta as ta
import ccxt
import matplotlib.pyplot as plt

# Strategy parameters
RSI_PERIOD = 14
EMA_PERIOD = 200
INITIAL_BALANCE = 2000
STOP_LOSS_PCT = 0.01  # 1%

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
df["RSI"] = ta.rsi(df["close"], length=RSI_PERIOD)
df["EMA"] = ta.ema(df["close"], length=EMA_PERIOD)
stoch = ta.stoch(df["high"], df["low"], df["close"])
df["STOCH_K"] = stoch["STOCHk_14_3_3"]
df["STOCH_D"] = stoch["STOCHd_14_3_3"]

# Backtest logic
position = False
entry_price = 0
stop_loss_price = 0
balance = INITIAL_BALANCE
units = 0
trades = []

for i in range(1, len(df)):
    row = df.iloc[i]
    prev = df.iloc[i - 1]

    # Entry: Stoch cross up in oversold zone & RSI crosses 50 up
    if (
        not position
        and row["STOCH_K"] < 20
        and row["STOCH_D"] < 20
        and prev["STOCH_K"] < row["STOCH_D"] < row["STOCH_K"]
        and prev["RSI"] < 50 < row["RSI"]
    ):
        entry_price = row["close"]
        stop_loss_price = entry_price * (1 - STOP_LOSS_PCT)
        units = balance / entry_price
        position = True
        entry_time = row.name
        print(f"[ENTRY] {entry_time} @ {entry_price:.2f}")

    # Exit: Stoch cross down in overbought zone & RSI crosses 50 down
    elif position:
        price = row["close"]
        stoch_cross_down = (
            row["STOCH_K"] > 80
            and row["STOCH_D"] > 80
            and row["STOCH_K"] < row["STOCH_D"] < prev["STOCH_K"]
        )
        rsi_cross_down = row["RSI"] < 50 < prev["RSI"]
        stop_hit = price <= stop_loss_price

        if stop_hit or (stoch_cross_down and rsi_cross_down):
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

# Final results
print(f"\nFinal Balance: ${balance:.2f}")
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
    plt.figure(figsize=(14, 6))
    plt.plot(df["close"], label="Close Price", alpha=0.7)
    for trade in trades:
        plt.axvline(trade["entry_time"], color="green", linestyle="--", alpha=0.6)
        plt.axvline(trade["exit_time"], color="red", linestyle="--", alpha=0.6)
    plt.title("Stochastic Strategy Backtest (pandas-ta)")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig("images/stochastic_strategy")