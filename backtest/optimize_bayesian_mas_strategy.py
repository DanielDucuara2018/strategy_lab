import pandas as pd
import numpy as np
import optuna
from pathlib import Path
import pandas_ta as ta


CURRENT_DIR = Path(__file__).parent
IMAGES_DIR = CURRENT_DIR.joinpath("images")
DATA_DIR = CURRENT_DIR.joinpath("data")

# --- Load Data ---
SYMBOL = "BTC/USDT"
TIMEFRAME_1h = "1h"
TIMEFRAME_1d = "1d"

def get_data(symbol: str, timeframe: str):
    df = pd.read_csv(DATA_DIR.joinpath(f"{symbol.replace("/", "")}_{timeframe}.csv"))
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    df.set_index("timestamp", inplace=True)
    return df.drop_duplicates()

def backtest_advanced(df, fast, slow, macd_fast, macd_slow, macd_signal,
                      commission=0.0004, slippage=0.0005, initial_balance=2000):
    df = df.copy()
    df["FAST"] = ta.sma(df["close"], length=fast)
    df["SLOW"] = ta.sma(df["close"], length=slow)
    df["SPREAD"] = df["FAST"] - df["SLOW"]
    df["SPREAD_SIGN"] = df["SPREAD"].apply(lambda x: 1 if x > 0 else -1)
    # df["RSI"] = ta.rsi(df["close"],rsi_period)
    macd = ta.macd(df["close"], macd_fast, macd_slow, macd_signal)
    df["MACD"], df["MACD_SIGNAL"] = macd[f"MACD_{macd_fast}_{macd_slow}_{macd_signal}"], macd[f"MACDs_{macd_fast}_{macd_slow}_{macd_signal}"]
    # df["BB_UPPER"], df["BB_LOWER"] = bollinger_bands(df["close"], period=bb_period, num_std=bb_mult)
    # df["ADX"] = adx(df, adx_period)
    # df["ATR"] = atr(df, atr_period)
    # df["ATR_MA"] = df["ATR"].rolling(window=atr_ma_period).mean()

    # Compute 200-day SMA for trend filter
    # df_1d[f"SMA{trend_sma_period}"] = sma(df_1d["close"], trend_sma_period)
    # df_1d["BULLISH_TREND"] = df_1d["close"] > df_1d[f"SMA{trend_sma_period}"]
    # df["BULLISH_TREND"] = df_1d["BULLISH_TREND"].reindex(df.index, method="ffill")

    balance = initial_balance
    peak_balance = initial_balance
    max_drawdown = 0
    trades = []
    position = False
    units = 0
    entry_price = 0
    signal_count = 0    

    for i in range(2, len(df)):
        row, prev, prev2 = df.iloc[i], df.iloc[i-1], df.iloc[i-2]
        # rsi_ok = row["RSI"] < rsi_threshold
        macd_ok = row["MACD"] > row["MACD_SIGNAL"]
        # bb_ok = row["close"] < row["BB_LOWER"]
        # adx_ok = row["ADX"] > adx_thresh
        # bullish_trend = row["BULLISH_TREND"]

        enter_long = (
            not position
            and prev2["SPREAD_SIGN"] == -1 and prev["SPREAD_SIGN"] == -1 and row["SPREAD_SIGN"] == 1
            # and rsi_ok
            and macd_ok
            # and bb_ok
            # and adx_ok
            # and bullish_trend
        )

        exit_long = (
            position
            and (
                prev2["SPREAD_SIGN"] == 1 and prev["SPREAD_SIGN"] == 1 and row["SPREAD_SIGN"] == -1
                # or (row["RSI"] > rsi_exit)
                # or (row["MACD"] < row["MACD_SIGNAL"])
            )
        )


        if enter_long:
            entry_price = row["close"] * (1 + slippage + commission)
            units = balance / entry_price
            position = True
            entry_time = row.name
            signal_count += 1

        # elif exit_long:
        elif exit_long:
            exit_price = row["close"] * (1 - slippage - commission)
            pnl = (exit_price - entry_price) * units
            balance += pnl
            trades.append(pnl)
            peak_balance = max(peak_balance, balance)
            drawdown = (peak_balance - balance) / peak_balance
            max_drawdown = max(max_drawdown, drawdown)
            position = False
            units = 0

    print(f"Total Trades: {len(trades)}, Entry Signals Triggered: {signal_count}")
    if not trades:
        return initial_balance, 0, 0, 0

    win_rate = len([p for p in trades if p > 0]) / len(trades)
    positive_sum = sum([p for p in trades if p > 0])
    negative_sum = abs(sum([p for p in trades if p < 0]))
    if negative_sum == 0:
        profit_factor = 10.0  # cap to avoid infinity
    else:
        profit_factor = positive_sum / negative_sum   
    return balance, win_rate, profit_factor, max_drawdown

# --- Optuna Objective Function ---
def objective(trial):

    df_1h = get_data(SYMBOL, TIMEFRAME_1h)
    df_1d = get_data(SYMBOL, TIMEFRAME_1d)

    fast = trial.suggest_int("fast", 5, 80)              # allow quicker signals
    slow = trial.suggest_int("slow", 30, 250)            # broader trend detection
    # rsi_period = trial.suggest_int("rsi_period", 5, 30)  # from fast to slower RSI
    # rsi_threshold = trial.suggest_int("rsi_threshold", 30, 70)  # covers oversold to neutral
    macd_fast = trial.suggest_int("macd_fast", 5, 20)    # shorter EMA for quick signals
    macd_slow = trial.suggest_int("macd_slow", 15, 50)   # slower EMA, must be > fast
    macd_signal = trial.suggest_int("macd_signal", 5, 20) # wider smoothing possibilities
    # bb_period = trial.suggest_int("bb_period", 15, 25)
    # bb_mult = trial.suggest_float("bb_mult", 1.5, 2.5)
    # adx_period = trial.suggest_int("adx_period", 10, 20)
    # adx_thresh = trial.suggest_float("adx_thresh", 15, 30)
    # rsi_exit = trial.suggest_int("rsi_exit", 60, 80)
    # atr_period = trial.suggest_int("atr_period", 10, 20)
    # atr_ma_period = trial.suggest_int("atr_ma_period", 2, 5)
    # trail_mult = trial.suggest_float("trail_mult", 1.0, 3.0)
    # trend_sma_period = 0 # trial.suggest_int("trend_sma_period", 10, 300)  # from short trend to 1-year


    if fast >= slow or macd_fast >= macd_slow:
        return -9999

    final_balance, win_rate, profit_factor, max_drawdown = backtest_advanced(
        df_1h, fast, slow, macd_fast, macd_slow, macd_signal
    )

    score = (final_balance - 2000) \
            + (profit_factor * 500) \
            + (win_rate * 1000) \
            - (max_drawdown * 2000)

    return score

# --- Launch Optimization ---
study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=1000, n_jobs=-1)

# --- Results ---
print("\nBest Parameters Found:")
print(study.best_params)
print(f"Best Final Balance: ${study.best_value:.2f}")

# Save study to csv
df_study = study.trials_dataframe()
df_study.to_csv(DATA_DIR.joinpath("optuna_mas_optimization.csv"), index=False)
