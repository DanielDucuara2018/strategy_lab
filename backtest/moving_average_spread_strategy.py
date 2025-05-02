import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from pathlib import Path

CURRENT_DIR = Path(__file__).parent
IMAGES_DIR = CURRENT_DIR.joinpath("images")
DATA_DIR = CURRENT_DIR.joinpath("data")

# --- Parameters ---
INITIAL_BALANCE = 2000
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
FAST_EMA = 25
SLOW_EMA = 111
RSI_PERIOD = 10
RSI_THRESHOLD = 50
MACD_FAST = 10
MACD_SLOW = 26
MACD_SIGNAL = 10
# BB_PERIOD = 19
# BB_MULT = 2.050230528935784
ADX_PERIOD = 13
ADX_THRESHOLD = 26.487381358163116  # Confirm trending conditions

ATR_PERIOD = 10
ATR_TRAIL_MULTIPLIER = 1.365649182010661
STOP_LOSS_ATR_MULTIPLIER = 1.853263443798225
TAKE_PROFIT_ATR_MULTIPLIER = 2.051437509435095
ATR_THRESHOLD = 50  # Minimum ATR value to enter trades
COMMISSION = 0.0004  # 0.04% per trade
SLIPPAGE = 0.0005  # 0.05% slippage

# --- Fetch Data ---
df = pd.read_csv(DATA_DIR.joinpath(f"{SYMBOL.replace("/","")}_{TIMEFRAME}.csv"))
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.set_index('timestamp', inplace=True)
df = df.drop_duplicates()

# --- Indicators ---
df["FAST"] = ta.sma(df["close"], length=FAST_EMA)
df["SLOW"] = ta.sma(df["close"], length=SLOW_EMA)
df["SPREAD"] = df["FAST"] - df["SLOW"]
df["SPREAD_SIGN"] = df["SPREAD"].apply(lambda x: 1 if x > 0 else -1)
df["RSI"] = ta.rsi(df["close"], length=RSI_PERIOD)
macd = ta.macd(df["close"], MACD_FAST, MACD_SLOW, MACD_SIGNAL)
df["MACD"], df["MACD_SIGNAL"] = macd[f"MACD_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}"], macd[f"MACDs_{MACD_FAST}_{MACD_SLOW}_{MACD_SIGNAL}"]
# bbands = ta.bbands(df['close'], period=BB_PERIOD, std=BB_MULT)
# df['BB_UPPER'], df['BB_LOWER'] = bbands[f"BBU_5_{BB_MULT}"], bbands[f"BBL_5_{BB_MULT}"]
df["ADX"] = ta.adx(df["high"], df["low"], df["close"], length=ADX_PERIOD)[f"ADX_{ADX_PERIOD}"]

df["ATR"] = ta.atr(df["high"], df["low"], df["close"], length=ATR_PERIOD)
df["ATR_MA"] = df["ATR"].rolling(50).mean()

# --- Backtest Variables ---
position = False
entry_price = 0
balance = INITIAL_BALANCE
units = 0
stop_loss = 0
take_profit = 0
trades = []

# --- Backtest Logic ---
for i in range(2, len(df)):
    row = df.iloc[i]
    prev = df.iloc[i - 1]
    prev2 = df.iloc[i - 2]

    enter_long = (
        not position
        and prev2["SPREAD_SIGN"] == -1 and prev["SPREAD_SIGN"] == -1 and row["SPREAD_SIGN"] == 1
        and row['RSI'] > RSI_THRESHOLD
        and row['MACD'] > row['MACD_SIGNAL']
        # and row['close'] < row['BB_LOWER']
        and row['ADX'] > ADX_THRESHOLD

        # and row["close"] > row["EMA_FAST"]
        # and row["ATR"] > row["ATR_MA"]
        # and trend_bullish
    )

    exit_long = (
        position
        and prev2["SPREAD_SIGN"] == 1 and prev["SPREAD_SIGN"] == 1 and row["SPREAD_SIGN"] == -1
        # and row["close"] < (row["close"] - ATR_TRAIL_MULTIPLIER * row["ATR"])
    )

    # --- Entry Conditions ---
    if enter_long:
        entry_price = row["close"] * (1 + SLIPPAGE + COMMISSION)
        units = balance / entry_price
        position = True
        entry_time = row.name
        print(f"[ENTRY] {entry_time} @ {entry_price:.2f}")


    # --- Exit Conditions ---
    elif exit_long:
        exit_price = row["close"] * (1 - SLIPPAGE - COMMISSION)
        pnl = (exit_price - entry_price) * units
        exit_time = row.name
        print(f"[LONG EXIT] {exit_time} @ {exit_price:.2f}")
        trades.append({
            "entry_time": entry_time,
            "exit_time": exit_time,
            "entry_price": entry_price,
            "exit_price": exit_price,
            "pnl": pnl,
            "return_pct": pnl / (units * entry_price) * 100,
            "old_balance": balance,
            "new_balance": balance + pnl
        })
        balance += pnl
        position = False
        units = 0 

# --- Results ---
print(f"\nFinal Balance: ${balance:.2f}")

if trades:
    trade_df = pd.DataFrame(trades)
    print("\nTrade Summary:")
    print(trade_df)

    # Performance Metrics
    wins = trade_df[trade_df["pnl"] > 0]
    losses = trade_df[trade_df["pnl"] <= 0]
    total_wins = wins["pnl"].sum()
    total_losses = abs(losses["pnl"].sum())
    value_weighted_win_rate = total_wins / (total_wins + total_losses) * 100 if (total_wins + total_losses) > 0 else 0
    win_rate = len(wins) / len(trade_df) * 100
    profit_factor = total_wins / total_losses if total_losses != 0 else float("inf")
    max_drawdown = (trade_df["pnl"].cumsum().cummax() - trade_df["pnl"].cumsum()).max()
    total_pnl = trade_df["pnl"].sum()

    print("\nStats:")
    print(f"Total Trades: {len(trade_df)}")
    print(f"Win Trades: {len(wins)}")
    print(f"Lose Trades: {len(losses)}")
    print(f"Max win: ${wins["pnl"].max():.2f}")
    print(f"Max lose: ${losses["pnl"].min():.2f}")
    print(f"Win Rate (Count-Based): {win_rate:.2f}%")
    print(f"Win Rate (PnL-Weighted): {value_weighted_win_rate:.2f}%")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Max Drawdown: ${max_drawdown:.2f}")
    print(f"Total PnL: ${total_pnl:.2f}")
    print(f"Final Balance: ${(total_pnl + INITIAL_BALANCE):.2f}")

    # Plot
    plt.figure(figsize=(14, 6))
    plt.plot(df["close"], label="Close Price", alpha=0.7)
    for trade in trades:
        plt.axvline(trade["entry_time"], color="green", linestyle="--", alpha=0.6)
        plt.axvline(trade["exit_time"], color="red", linestyle="--", alpha=0.6)
    plt.title("MAS (Moving Average Spread) Strategy Backtest")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(IMAGES_DIR.joinpath(f"{SYMBOL.replace("/","")}_mas_strategy"))

    # --- Plot Equity Curve ---
    plt.figure(figsize=(12,6))
    plt.plot(trade_df["old_balance"])
    plt.title("MAS (Moving Average Spread) Strategy Equity Curve")
    plt.xlabel("Trades")
    plt.ylabel("Balance")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(IMAGES_DIR.joinpath(f"{SYMBOL.replace("/","")}_mas_equity_curve.png"))
