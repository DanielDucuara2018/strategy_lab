from pathlib import Path

import numpy as np
import pandas as pd
import pandas_ta as ta

CURRENT_DIR = Path(__file__).parent
IMAGES_DIR = CURRENT_DIR.joinpath("images")
DATA_DIR = CURRENT_DIR.joinpath("data")

# --- Parameters ---
INITIAL_BALANCE = 2000
SYMBOL = "BTC/USDT"
TIMEFRAME_1H = "1h"
TIMEFRAME_1D = "1d"
FAST_EMA = 60
SLOW_EMA = 215
RSI_PERIOD = 12
RSI_THRESHOLD = 45
# RSI_EXIT = 64
MACD_FAST = 8
MACD_SLOW = 28
MACD_SIGNAL = 12
# BB_PERIOD = 19
# BB_MULT = 2.050230528935784
# ADX_PERIOD = 13
# ADX_THRESHOLD = 26.487381358163116  # Confirm trending conditions
ATR_PERIOD = 16
ATR_MA_PERIOD = 2
ATR_TRAIL_MULTIPLIER = 1.7641142354814043

# STOP_LOSS_ATR_MULTIPLIER = 1.853263443798225
# TAKE_PROFIT_ATR_MULTIPLIER = 2.051437509435095
# ATR_THRESHOLD = 50  # Minimum ATR value to enter trades
# COMMISSION = 0.0004  # 0.04% per trade
# SLIPPAGE = 0.0005  # 0.05% slippage


# --- Fetch Data ---
def get_data(symbol: str, timeframe: str):
    df = pd.read_csv(DATA_DIR.joinpath(f"{symbol.replace('/', '')}_{timeframe}.csv"))
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    return df.drop_duplicates()


def compute_indicators(
    df,
    df_1d,
    fast,
    slow,
    rsi_period,
    macd_fast,
    macd_slow,
    macd_signal,
    trend_sma_period,
):
    # --- Indicators ---
    df["FAST"] = ta.sma(df["close"], length=fast)
    df["SLOW"] = ta.sma(df["close"], length=slow)
    df["SPREAD"] = df["FAST"] - df["SLOW"]
    df["SPREAD_SIGN"] = np.where(df["SPREAD"] > 0, 1, -1)
    df["RSI"] = ta.rsi(df["close"], length=rsi_period)
    macd = ta.macd(df["close"], macd_fast, macd_slow, macd_signal)
    df["MACD"], df["MACD_SIGNAL"] = (
        macd[f"MACD_{macd_fast}_{macd_slow}_{macd_signal}"],
        macd[f"MACDs_{macd_fast}_{macd_slow}_{macd_signal}"],
    )
    # bbands = ta.bbands(df['close'], period=BB_PERIOD, std=BB_MULT)
    # df['BB_UPPER'], df['BB_LOWER'] = bbands[f"BBU_5_{BB_MULT}"], bbands[f"BBL_5_{BB_MULT}"]
    # df["ADX"] = ta.adx(df["high"], df["low"], df["close"], length=ADX_PERIOD)[f"ADX_{ADX_PERIOD}"]
    # df["ATR"] = ta.atr(df["high"], df["low"], df["close"], length=atr_period)
    # df["ATR_MA"] = df["ATR"].rolling(atr_ma_period).mean()

    # Compute 200-day SMA for trend filter
    df_1d[f"SMA{trend_sma_period}"] = ta.sma(df_1d["close"], trend_sma_period)
    df_1d["BULLISH_TREND"] = df_1d["close"] > df_1d[f"SMA{trend_sma_period}"]
    df["BULLISH_TREND"] = df_1d["BULLISH_TREND"].reindex(df.index, method="ffill")
    # df_1d["BULLISH_TREND"] = df_1d["close"] > df_1d[f"SMA{trend_sma_period}"]
    # df_1d["BULLISH_TREND"] = df_1d["BULLISH_TREND"].shift(1, fill_value=False)  # <- shift by 1 day
    # df["BULLISH_TREND"] = df.index.to_series().dt.floor("D").map(df_1d["BULLISH_TREND"])
    return df, df_1d


def backtest_advanced(
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

    # --- Backtest Variables ---
    balance = initial_balance
    peak_balance = initial_balance
    max_drawdown = 0
    trades = []
    position = False
    units = 0
    entry_price = 0
    # trailing_stop = None

    # --- Backtest Logic ---
    for i in range(2, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i - 1]
        prev2 = df.iloc[i - 2]

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

    if not trades:
        return initial_balance, 0, 0, 0, []

    win_rate = len([p["pnl"] for p in trades if p["pnl"] > 0]) / len(trades)
    positive_sum = sum([p["pnl"] for p in trades if p["pnl"] > 0])
    negative_sum = abs(sum([p["pnl"] for p in trades if p["pnl"] < 0]))
    if negative_sum == 0:
        profit_factor = 10.0  # cap to avoid infinity
    else:
        profit_factor = positive_sum / negative_sum
    return balance, win_rate, profit_factor, max_drawdown, trades
