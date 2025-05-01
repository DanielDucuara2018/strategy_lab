import pandas as pd
import numpy as np
import optuna
import matplotlib.pyplot as plt
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

def atr(df, period):
    high_low = df['high'] - df['low']
    high_close = np.abs(df['high'] - df['close'].shift())
    low_close = np.abs(df['low'] - df['close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    return tr.rolling(window=period).mean()

def backtest_advanced(df, fast, slow, atr_period, atr_trail_mult, stop_loss_mult, take_profit_mult,
                      commission=0.0004, slippage=0.0005, initial_balance=2000):
    df = df.copy()
    df['FAST'] = sma(df['close'], fast)
    df['SLOW'] = sma(df['close'], slow)
    df['SPREAD'] = df['FAST'] - df['SLOW']
    df['SPREAD_SIGN'] = np.where(df['SPREAD'] > 0, 1, -1)
    df['ATR'] = atr(df, atr_period)

    balance = initial_balance
    peak_balance = initial_balance
    max_drawdown = 0
    trades = []
    position = False
    units = 0
    entry_price = 0

    for i in range(2, len(df)):
        row, prev, prev2 = df.iloc[i], df.iloc[i-1], df.iloc[i-2]

        enter_long = not position and prev2['SPREAD_SIGN'] == -1 and prev['SPREAD_SIGN'] == -1 and row['SPREAD_SIGN'] == 1
        exit_long = position and (prev2['SPREAD_SIGN'] == 1 and prev['SPREAD_SIGN'] == 1 and row['SPREAD_SIGN'] == -1)

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
    atr_period = trial.suggest_int('atr_period', 10, 20)
    atr_trail_mult = trial.suggest_float('atr_trail_mult', 1.0, 2.0)
    stop_loss_mult = trial.suggest_float('stop_loss_mult', 1.0, 2.0)
    take_profit_mult = trial.suggest_float('take_profit_mult', 2.0, 4.0)

    if fast >= slow:
        return -9999

    final_balance, win_rate, profit_factor, max_drawdown = backtest_advanced(
        df, fast, slow, atr_period, atr_trail_mult, stop_loss_mult, take_profit_mult
    )

    # Scoring system: balance + (profit_factor bonus) - (drawdown penalty)
    score = (final_balance - 2000) \
            + (profit_factor * 500) \
            + (win_rate * 1000) \
            - (max_drawdown * 2000)

    return score

# --- Launch Optimization ---
study = optuna.create_study(direction='maximize')
study.optimize(objective, n_trials=300, n_jobs=-1)  # n_jobs=-1 utilise tous les cores dispo

# --- Results ---
print("\nBest Parameters Found:")
print(study.best_params)
print(f"Best Final Balance: ${study.best_value:.2f}")

# Save study to csv
df_study = study.trials_dataframe()
df_study.to_csv(DATA_DIR.joinpath("optuna_mas_optimization.csv"), index=False)
