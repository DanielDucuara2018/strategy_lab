import ccxt
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt

# Strategy parameters
RSI_PERIOD = 2
EMA_PERIOD = 200
ADX_PERIOD = 14
ATR_PERIOD = 14
BBW_PERIOD = 20
INITIAL_BALANCE = 2000
STOP_LOSS_PCT = 0.05 # 5%
PERCENTAGE_GAIN = 0.1 # 10%
ADX_THRESHOLD = 20  # Trend strength filter

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

# Indicators
df["RSI"] = ta.rsi(df["close"], length=RSI_PERIOD)
df["EMA"] = ta.ema(df["close"], length=EMA_PERIOD)
df["ATR"] = ta.atr(df["high"], df["low"], df["close"], length=ATR_PERIOD)
df["ATR_MA"] = df["ATR"].rolling(20).mean()
df["ADX"] = ta.adx(df["high"], df["low"], df["close"], length=ADX_PERIOD)[f"ADX_{ADX_PERIOD}"]
bb = ta.bbands(df["close"], length=BBW_PERIOD)
df["BBL"] = bb[f"BBL_{BBW_PERIOD}_2.0"]
df["BBU"] = bb[f"BBU_{BBW_PERIOD}_2.0"]
df["BBW"] = (df["BBU"] - df["BBL"]) / df["close"]  # Normalized BBW
df["BBW_SMA"] = df["BBW"].rolling(20).mean()

# Backtest setup
position = False
entry_price = 0
stop_loss_price = 0
balance = INITIAL_BALANCE
units = 0
trades = []

for i in range(1, len(df)):
    row = df.iloc[i]
    prev = df.iloc[i - 1]

    # Entry: RSI cross up from oversold + price above EMA + ADX strong
    if (
        not position
        # RSI crosses above oversold (10)
        and prev["RSI"] < 10 < row["RSI"]
        # Price is above long-term EMA (bullish bias)
        and row["close"] > row["EMA"]
        # ADX confirms strong trend (optional: ADX > 20 or 25)
        and row["ADX"] > 20
        # ATR filter: current volatility > historical volatility
        # and row["ATR"] > row["ATR_MA"]
        # BBW filter: current BB width > average width
        # and row["BBW"] > row["BBW_SMA"]
    ):
        entry_price = row["close"]
        stop_loss_price = entry_price * (1 - STOP_LOSS_PCT)
        units = balance / entry_price
        position = True
        entry_time = row.name
        print(f"[ENTRY] {entry_time} @ {entry_price:.2f}")

    # Exit: RSI crosses down from overbought + price above EMA or stop loss
    elif position:
        price = row["close"]
        rsi_down = row["RSI"] < 90 < prev["RSI"]
        stop_hit = price <= stop_loss_price
        profit_hit = (price - entry_price) / entry_price >= PERCENTAGE_GAIN
        # vol_shrinks = row["ATR"] < row["ATR_MA"] or row["BBW"] < row["BBW_SMA"]

        if stop_hit or (profit_hit and price > row["EMA"] and rsi_down): # or vol_shrinks:
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
                "return_pct": (price - entry_price) / entry_price * 100,
                "old_balance": balance,
                "new_balance": sell_balance
            })
            balance = sell_balance

# Summary
print(f"\nFinal Balance: ${balance:.2f}")
if trades:
    trade_df = pd.DataFrame(trades)
    print("\nTrade Summary:")
    print(trade_df)

    # Performance Metrics
    # Traditional metrics
    wins = trade_df[trade_df['pnl'] > 0]
    losses = trade_df[trade_df['pnl'] <= 0]

    # Total profits and losses
    total_wins = wins['pnl'].sum()
    total_losses = abs(losses['pnl'].sum())  # use abs for losses

    # Value-weighted win rate (profit share)
    value_weighted_win_rate = total_wins / (total_wins + total_losses) * 100 if (total_wins + total_losses) > 0 else 0

    # Existing metrics
    win_rate = len(wins) / len(trade_df) * 100
    profit_factor = total_wins / total_losses if total_losses != 0 else float('inf')

    print("\nStats:")
    print(f"Total Trades: {len(trade_df)}")
    print(f"Win Trades: {len(wins)}")
    print(f"Lose Trades: {len(losses)}")
    print(f"Max win: ${wins['pnl'].max():.2f}")
    print(f"Max lose: ${losses['pnl'].min():.2f}")
    print(f"Win Rate (Count-Based): {win_rate:.2f}%")
    print(f"Win Rate (PnL-Weighted): {value_weighted_win_rate:.2f}%")  # 💥 New metric here
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Total PnL: ${trade_df['pnl'].sum():.2f}")

    # Plot
    plt.figure(figsize=(14, 6))
    plt.plot(df["close"], label="Close Price", alpha=0.7)
    for trade in trades:
        plt.axvline(trade["entry_time"], color="green", linestyle="--", alpha=0.6)
        plt.axvline(trade["exit_time"], color="red", linestyle="--", alpha=0.6)
    plt.title("Enhanced RSI Strategy Backtest")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig("images/rsi_strategy")
