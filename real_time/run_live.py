import ccxt
import datetime
import time
import pandas as pd
from pathlib import Path
from backtest.moving_average_spread_strategy import (
    compute_indicators,
    get_data,
    INITIAL_BALANCE,
    TIMEFRAME_1H,
    TIMEFRAME_1D,
    SYMBOL,
    # FAST_EMA,
    # SLOW_EMA,
    # RSI_PERIOD,
    # RSI_THRESHOLD,
    # MACD_FAST,
    # MACD_SLOW,
    # MACD_SIGNAL,
    # ATR_PERIOD,
    # ATR_MA_PERIOD,
    # ATR_TRAIL_MULTIPLIER
)


CURRENT_DIR = Path(__file__).parent
IMAGES_DIR = CURRENT_DIR.joinpath("images")
DATA_DIR = CURRENT_DIR.joinpath("data")

exchange = ccxt.binance()


# --- Fetch Candles ---
def fetch_candles(symbol: str, timeframe: str, limit=10):
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe=timeframe, limit=limit)
    df = pd.DataFrame(
        ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
    )
    df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
    df.set_index("timestamp", inplace=True)
    df = df.drop_duplicates()
    return df


def update_data(df, df_new):
    df_combined = pd.concat([df, df_new])
    df_combined = df_combined[~df_combined.index.duplicated(keep="last")]
    return df_combined.sort_index()


def wait_for_next_candle(timeframe="1h"):
    now = datetime.datetime.now()
    if timeframe == "1h":
        wait_seconds = 3600 - (now.minute * 60 + now.second)
    time.sleep(wait_seconds + 2)  # buffer time


def run_live(
    df,
    df_1d,
    fast,
    slow,
    rsi_period,
    rsi_threshold,
    macd_fast,
    macd_slow,
    macd_signal,
    trend_sma_period,  # atr_period, atr_ma_period, atr_trail_mult,
    commission=0.0004,
    slippage=0.0005,
    initial_balance=INITIAL_BALANCE,
    mode="backtest",
):
    df, df_1d = compute_indicators(
        df,
        df_1d,
        fast,
        slow,
        rsi_period,
        macd_fast,
        macd_slow,
        macd_signal,
        trend_sma_period,
    )

    balance = initial_balance
    peak_balance = initial_balance
    max_drawdown = 0
    trades = []
    position = False
    units = 0
    entry_price = 0

    print("[INFO] running live strategy")
    while True:
        df_new, df_1d_new = (
            fetch_candles(SYMBOL, TIMEFRAME_1H, 50),
            fetch_candles(SYMBOL, TIMEFRAME_1D, 50),
        )
        df, df_1d = update_data(df, df_new), update_data(df_1d, df_1d_new)
        df, df_1d = compute_indicators(
            df,
            df_1d,
            fast,
            slow,
            rsi_period,
            macd_fast,
            macd_slow,
            macd_signal,
            trend_sma_period,
        )

        row = df.iloc[-1]
        prev = df.iloc[-2]
        prev2 = df.iloc[-3]

        # if np.isnan(row["ATR_MA"]):
        #     continue

        enter_long = (
            not position
            and prev2["SPREAD_SIGN"] == -1
            and prev["SPREAD_SIGN"] == -1
            and row["SPREAD_SIGN"] == 1
            and row["RSI"] < rsi_threshold
            and row["MACD"] > row["MACD_SIGNAL"]
            # and row['close'] < row['BB_LOWER']
            # and row['ADX'] > ADX_THRESHOLD
            # and row["close"] > row["EMA_FAST"]
            # and row["ATR"] > row["ATR_MA"]
            and row["BULLISH_TREND"]
        )

        exit_long = position and (
            prev2["SPREAD_SIGN"] == 1
            and prev["SPREAD_SIGN"] == 1
            and row["SPREAD_SIGN"] == -1
            # or (row['RSI'] > RSI_EXIT)
            # or (row['MACD'] < row['MACD_SIGNAL'])
        )

        # --- Entry Conditions ---
        if enter_long:
            entry_price = row["close"] * (1 + slippage + commission)
            units = balance / entry_price
            position = True
            entry_time = row.name
            if mode == "backtest":
                print(f"[ENTRY] {entry_time} @ {entry_price:.2f}")
            # trailing_stop = row['close'] - atr_trail_mult * row['ATR_MA']

        # --- Exit Conditions ---
        elif exit_long:
            # elif position and trailing_stop is not None:
            #     trailing_stop = max(trailing_stop, row['close'] - atr_trail_mult * row['ATR_MA'])
            #     if row['close'] < trailing_stop:
            exit_price = row["close"] * (1 - slippage - commission)
            pnl = (exit_price - entry_price) * units
            exit_time = row.name
            if mode == "backtest":
                print(f"[LONG EXIT] {exit_time} @ {exit_price:.2f}")
            trades.append(
                {
                    "entry_time": entry_time,
                    "exit_time": exit_time,
                    "entry_price": entry_price,
                    "exit_price": exit_price,
                    "pnl": pnl,
                    "return_pct": pnl / (units * entry_price) * 100,
                    "old_balance": balance,
                    "new_balance": balance + pnl,
                }
            )
            balance += pnl
            peak_balance = max(peak_balance, balance)
            drawdown = (peak_balance - balance) / peak_balance
            max_drawdown = max(max_drawdown, drawdown)
            position = False
            units = 0

        wait_for_next_candle(TIMEFRAME_1H)


df_1h, df_1d = get_data(SYMBOL, TIMEFRAME_1H), get_data(SYMBOL, TIMEFRAME_1D)
final_balance, win_rate, profit_factor, max_drawdown, trades = run_live(
    df_1h,
    df_1d,
    # **{'fast': 6, 'slow': 67, 'rsi_period': 25, 'rsi_threshold': 65, 'macd_fast': 5, 'macd_slow': 48, 'macd_signal': 12, 'trend_sma_period': 10}
    # **{'fast': 8, 'slow': 82, 'rsi_period': 27, 'rsi_threshold': 68, 'macd_fast': 19, 'macd_slow': 29, 'macd_signal': 7, 'trend_sma_period': 10}
    **{
        "fast": 12,
        "slow": 70,
        "rsi_period": 29,
        "rsi_threshold": 68,
        "macd_fast": 20,
        "macd_slow": 40,
        "macd_signal": 17,
        "trend_sma_period": 12,
    },
)
