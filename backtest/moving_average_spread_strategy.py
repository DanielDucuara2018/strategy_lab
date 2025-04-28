import ccxt
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from pathlib import Path

CURRENT_DIR = Path(__file__).parent
IMAGES_DIR = CURRENT_DIR.joinpath("images")

# --- Parameters ---
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
FAST_EMA = 20
SLOW_EMA = 80
ATR_PERIOD = 14
ADX_PERIOD = 14
INITIAL_BALANCE = 2000
STOP_LOSS_ATR_MULTIPLIER = 1.5
TAKE_PROFIT_ATR_MULTIPLIER = 3.0
ATR_THRESHOLD = 50  # Minimum ATR value to enter trades
ADX_THRESHOLD = 20  # Confirm trending conditions
COMMISSION = 0.0004  # 0.04% per trade
SLIPPAGE = 0.0005  # 0.05% slippage

# --- Fetch Data ---
# Download BTC/USDT-like data
ohlcv = []
limit = 1000
init_date = pd.Timestamp("2017-01-01")
today = pd.Timestamp.today()
exchange = ccxt.binance()
while init_date < today:
    ohlcv += exchange.fetch_ohlcv(SYMBOL, since=init_date.value // 10**6, limit=limit, timeframe=TIMEFRAME)
    init_date += pd.Timedelta(1000, "h")

df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# --- Indicators ---
df['FAST'] = ta.sma(df['close'], length=FAST_EMA)
df['SLOW'] = ta.sma(df['close'], length=SLOW_EMA)
df['SPREAD'] = df['FAST'] - df['SLOW']
df['SPREAD_SIGN'] = df['SPREAD'].apply(lambda x: 1 if x > 0 else -1)   
# df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=ATR_PERIOD)
# df['ADX'] = ta.adx(df['high'], df['low'], df['close'], length=ADX_PERIOD)[f'ADX_{ADX_PERIOD}']

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
    current = df.iloc[i]
    prev = df.iloc[i - 1]
    prev2 = df.iloc[i - 2]

    spread_flip_up = prev2['SPREAD_SIGN'] == -1 and prev['SPREAD_SIGN'] == -1 and current['SPREAD_SIGN'] == 1
    spread_flip_down = prev2['SPREAD_SIGN'] == 1 and prev['SPREAD_SIGN'] == 1 and current['SPREAD_SIGN'] == -1

    # atr_ok = current['ATR'] > ATR_THRESHOLD
    # adx_ok = current['ADX'] > ADX_THRESHOLD

    # --- Entry Conditions ---
    if not position and spread_flip_up:
        entry_price = current['close'] * (1 + SLIPPAGE + COMMISSION)
        units = balance / entry_price
        position = 1
        entry_time = current.name
        print(f"[ENTRY] {entry_time} @ {entry_price:.2f}")


    # --- Exit Conditions ---
    elif position and spread_flip_down:
        exit_price = current['close'] * (1 - SLIPPAGE - COMMISSION)
        pnl = (exit_price - entry_price) * units
        exit_time = current.name
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
        position = None
        units = 0 

# --- Results ---
print(f"\nFinal Balance: ${balance:.2f}")

if trades:
    trade_df = pd.DataFrame(trades)
    print("\nTrade Summary:")
    print(trade_df)

    # Performance Metrics
    wins = trade_df[trade_df['pnl'] > 0]
    losses = trade_df[trade_df['pnl'] <= 0]
    total_wins = wins['pnl'].sum()
    total_losses = abs(losses['pnl'].sum())
    value_weighted_win_rate = total_wins / (total_wins + total_losses) * 100 if (total_wins + total_losses) > 0 else 0
    win_rate = len(wins) / len(trade_df) * 100
    profit_factor = total_wins / total_losses if total_losses != 0 else float('inf')
    max_drawdown = (trade_df['pnl'].cumsum().cummax() - trade_df['pnl'].cumsum()).max()

    print("\nStats:")
    print(f"Total Trades: {len(trade_df)}")
    print(f"Win Trades: {len(wins)}")
    print(f"Lose Trades: {len(losses)}")
    print(f"Max win: ${wins['pnl'].max():.2f}")
    print(f"Max lose: ${losses['pnl'].min():.2f}")
    print(f"Win Rate (Count-Based): {win_rate:.2f}%")
    print(f"Win Rate (PnL-Weighted): {value_weighted_win_rate:.2f}%")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Max Drawdown: ${max_drawdown:.2f}")
    print(f"Total PnL: ${trade_df['pnl'].sum():.2f}")

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
    plt.savefig(IMAGES_DIR.joinpath("mas_strategy"))
