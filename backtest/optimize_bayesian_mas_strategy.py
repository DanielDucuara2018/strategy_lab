import pandas as pd
import numpy as np
import optuna
from pathlib import Path

CURRENT_DIR = Path(__file__).parent
IMAGES_DIR = CURRENT_DIR.joinpath("images")
DATA_DIR = CURRENT_DIR.joinpath("data")

# --- Load Data ---
SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"
df = pd.read_csv(DATA_DIR.joinpath(f"{SYMBOL.replace('/', '')}_{TIMEFRAME}.csv"))
df['timestamp'] = pd.to_datetime(df['timestamp'])
df.set_index('timestamp', inplace=True)
df = df.drop_duplicates()

# --- Functions ---
def sma(series, length):
    return series.rolling(window=length).mean()

def ema(series, length):
    return series.ewm(span=length, adjust=False).mean()

def rsi(series, period=14):
    delta = series.diff()
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    avg_gain = pd.Series(gain).rolling(window=period).mean()
    avg_loss = pd.Series(loss).rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def macd(series, fast=12, slow=26, signal=9):
    ema_fast = ema(series, fast)
    ema_slow = ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def bollinger_bands(series, period=20, num_std=2):
    sma_ = sma(series, period)
    std = series.rolling(window=period).std()
    upper = sma_ + num_std * std
    lower = sma_ - num_std * std
    return upper, lower

def adx(df, period):
    up_move = df['high'].diff()
    down_move = df['low'].diff().abs()
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    tr = pd.concat([
        df['high'] - df['low'],
        (df['high'] - df['close'].shift()).abs(),
        (df['low'] - df['close'].shift()).abs()
    ], axis=1).max(axis=1)
    atr_val = tr.rolling(window=period).mean()
    plus_di = 100 * pd.Series(plus_dm).rolling(window=period).mean() / atr_val
    minus_di = 100 * pd.Series(minus_dm).rolling(window=period).mean() / atr_val
    dx = (np.abs(plus_di - minus_di) / (plus_di + minus_di)) * 100
    return dx.rolling(window=period).mean()


def backtest_advanced(df, fast, slow, rsi_period, rsi_threshold, macd_fast, macd_slow, macd_signal, adx_period, adx_thresh,
                      commission=0.0004, slippage=0.0005, initial_balance=2000):
    df = df.copy()
    df['FAST'] = sma(df['close'], fast)
    df['SLOW'] = sma(df['close'], slow)
    df['SPREAD'] = df['FAST'] - df['SLOW']
    df['SPREAD_SIGN'] = np.where(df['SPREAD'] > 0, 1, -1)
    df['RSI'] = rsi(df['close'], rsi_period)
    df['MACD'], df['MACD_SIGNAL'], df['MACD_HIST'] = macd(df['close'], macd_fast, macd_slow, macd_signal)
    # df['BB_UPPER'], df['BB_LOWER'] = bollinger_bands(df['close'], period=bb_period, num_std=bb_mult)
    df['ADX'] = adx(df, adx_period)

    balance = initial_balance
    peak_balance = initial_balance
    max_drawdown = 0
    trades = []
    position = False
    units = 0
    entry_price = 0

    for i in range(2, len(df)):
        row, prev, prev2 = df.iloc[i], df.iloc[i-1], df.iloc[i-2]
        rsi_ok = row['RSI'] < rsi_threshold
        macd_ok = row['MACD'] > row['MACD_SIGNAL']
        # bb_ok = row['close'] < row['BB_LOWER']
        adx_ok = row['ADX'] > adx_thresh


        enter_long = (
            not position
            and prev2['SPREAD_SIGN'] == -1 and prev['SPREAD_SIGN'] == -1 and row['SPREAD_SIGN'] == 1
            and rsi_ok
            and macd_ok
            # and bb_ok
            and adx_ok
        )

        exit_long = (
            position
            and (prev2['SPREAD_SIGN'] == 1 and prev['SPREAD_SIGN'] == 1 and row['SPREAD_SIGN'] == -1)
        )

        if enter_long:
            entry_price = row['close'] * (1 + slippage + commission)
            units = balance / entry_price
            position = True
            entry_time = row.name

        elif exit_long:
            exit_price = row['close'] * (1 - slippage - commission)
            pnl = (exit_price - entry_price) * units
            balance += pnl
            trades.append(pnl)
            peak_balance = max(peak_balance, balance)
            drawdown = (peak_balance - balance) / peak_balance
            max_drawdown = max(max_drawdown, drawdown)
            position = False
            units = 0

    if not trades:
        return initial_balance, 0, float('inf'), 0

    win_rate = len([p for p in trades if p > 0]) / len(trades)
    profit_factor = (sum([p for p in trades if p > 0]) / abs(sum([p for p in trades if p < 0]))) if sum([p for p in trades if p < 0]) != 0 else float('inf')
    return balance, win_rate, profit_factor, max_drawdown

# --- Optuna Objective Function ---
def objective(trial):
    fast = trial.suggest_int('fast', 10, 30)
    slow = trial.suggest_int('slow', 50, 120)
    rsi_period = trial.suggest_int('rsi_period', 10, 20)
    rsi_threshold = trial.suggest_int('rsi_threshold', 50, 70)
    macd_fast = trial.suggest_int('macd_fast', 8, 15)
    macd_slow = trial.suggest_int('macd_slow', 20, 30)
    macd_signal = trial.suggest_int('macd_signal', 5, 12)
    # bb_period = trial.suggest_int('bb_period', 15, 25)
    # bb_mult = trial.suggest_float('bb_mult', 1.5, 2.5)
    adx_period = trial.suggest_int('adx_period', 10, 20)
    adx_thresh = trial.suggest_float('adx_thresh', 15, 30)

    if fast >= slow or macd_fast >= macd_slow:
        return -9999

    final_balance, win_rate, profit_factor, max_drawdown = backtest_advanced(
        df, fast, slow, rsi_period, rsi_threshold, macd_fast, macd_slow, macd_signal, adx_period, adx_thresh
    )

    score = (final_balance - 2000) \
            + (profit_factor * 500) \
            + (win_rate * 1000) \
            - (max_drawdown * 2000)

    return score

# --- Launch Optimization ---
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=300, n_jobs=-1)

# --- Results ---
print("\nBest Parameters Found:")
print(study.best_params)
print(f"Best Final Balance: ${study.best_value:.2f}")

# Save study to csv
df_study = study.trials_dataframe()
df_study.to_csv(DATA_DIR.joinpath("optuna_mas_optimization.csv"), index=False)
