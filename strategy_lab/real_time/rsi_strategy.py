import ccxt
import pandas as pd
import pandas_ta as ta
import time

# Constants
TIMEFRAME = "1h"
SYMBOL = "BTC/USDT"
LOOKBACK_LIMIT = 300  # minimum for EMA 200 + indicators
FETCH_INTERVAL = 60 * 60  # seconds for 1h candle

# Strategy params
RSI_PERIOD = 2
EMA_PERIOD = 200
ADX_PERIOD = 14
ATR_PERIOD = 14
BBW_PERIOD = 20
INITIAL_BALANCE = 2000
STOP_LOSS_PCT = 0.05
PERCENTAGE_GAIN = 0.1
ADX_THRESHOLD = 20

# Initialize exchange
exchange = ccxt.binance({"enableRateLimit": True})

# State
position = False
entry_price = 0
stop_loss_price = 0
units = 0
balance = INITIAL_BALANCE
trades = []


# === Function to fetch + process candle data ===
def fetch_candles():
    print("Fetching initial historical data...")
    ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=LOOKBACK_LIMIT)
    df = pd.DataFrame(
        ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    return df


# === Function to update indicators ===
def update_indicators(df):
    df["RSI"] = ta.rsi(df["close"], length=RSI_PERIOD)
    df["EMA"] = ta.ema(df["close"], length=EMA_PERIOD)
    df["ATR"] = ta.atr(df["high"], df["low"], df["close"], length=ATR_PERIOD)
    df["ATR_MA"] = df["ATR"].rolling(20).mean()
    adx = ta.adx(df["high"], df["low"], df["close"], length=ADX_PERIOD)
    df["ADX"] = adx[f"ADX_{ADX_PERIOD}"]
    bb = ta.bbands(df["close"], length=BBW_PERIOD)
    df["BBL"] = bb[f"BBL_{BBW_PERIOD}_2.0"]
    df["BBU"] = bb[f"BBU_{BBW_PERIOD}_2.0"]
    df["BBW"] = (df["BBU"] - df["BBL"]) / df["close"]
    df["BBW_SMA"] = df["BBW"].rolling(20).mean()
    return df


# === Strategy Execution ===
def execute_strategy(df):
    global position, entry_price, stop_loss_price, balance, units, trades

    row = df.iloc[-1]
    prev = df.iloc[-2]

    rsi_down = row["RSI"] < 90 < prev["RSI"]
    profit_hit = (
        (row["close"] - entry_price) / entry_price >= PERCENTAGE_GAIN
        if position
        else False
    )
    stop_hit = row["close"] <= stop_loss_price if position else False
    vol_shrinks = row["ATR"] < row["ATR_MA"] or row["BBW"] < row["BBW_SMA"]

    if (
        not position
        and prev["RSI"] < 10 < row["RSI"]
        and row["close"] > row["EMA"]
        and row["ADX"] > ADX_THRESHOLD
    ):
        # Entry
        entry_price = row["close"]
        stop_loss_price = entry_price * (1 - STOP_LOSS_PCT)
        units = balance / entry_price
        position = True
        print(f"[{row.name}] ENTRY at {entry_price:.2f}")

    elif position:
        if (
            stop_hit
            or (profit_hit and row["close"] > row["EMA"] and (rsi_down or vol_shrinks))
            or vol_shrinks
        ):
            # Exit
            exit_price = row["close"]
            pnl = units * exit_price - balance
            print(f"[{row.name}] EXIT at {exit_price:.2f} | PnL: {pnl:.2f}")
            trades.append(
                {
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "entry_time": df.index[-2],
                    "exit_time": df.index[-1],
                    "pnl": pnl,
                }
            )
            balance += pnl
            position = False


# === Main loop ===
df = fetch_candles()
df = update_indicators(df)

while True:
    try:
        # Fetch the most recent candle
        new_candle = exchange.fetch_ohlcv(SYMBOL, timeframe=TIMEFRAME, limit=1)[-1]
        ts = pd.to_datetime(new_candle[0], unit="ms")

        # Only update if new candle
        if ts > df.index[-1]:
            new_df = pd.DataFrame(
                [new_candle],
                columns=["timestamp", "open", "high", "low", "close", "volume"],
            )
            new_df["timestamp"] = pd.to_datetime(new_df["timestamp"], unit="ms")
            new_df.set_index("timestamp", inplace=True)
            df = pd.concat([df, new_df]).tail(LOOKBACK_LIMIT)
            df = update_indicators(df)
            execute_strategy(df)

        time.sleep(FETCH_INTERVAL)

    except Exception as e:
        print(f"Error: {e}")
        time.sleep(30)
