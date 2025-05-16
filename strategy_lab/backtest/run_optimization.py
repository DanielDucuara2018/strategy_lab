from pathlib import Path

import optuna
from moving_average_spread_strategy import (
    INITIAL_BALANCE,
    SYMBOL,
    TIMEFRAME_1D,
    TIMEFRAME_1H,
    backtest_advanced,
    get_data,
)

CURRENT_DIR = Path(__file__).parent
OPTI_DIR = CURRENT_DIR.joinpath("optimization")


# --- Optuna Objective Function ---
def objective(trial):
    df_1h = get_data(SYMBOL, TIMEFRAME_1H)
    df_1d = get_data(SYMBOL, TIMEFRAME_1D)

    fast = trial.suggest_int("fast", 5, 80)  # allow quicker signals
    slow = trial.suggest_int("slow", 30, 250)  # broader trend detection
    rsi_period = trial.suggest_int("rsi_period", 5, 30)  # from fast to slower RSI
    rsi_threshold = trial.suggest_int(
        "rsi_threshold", 30, 70
    )  # covers oversold to neutral
    # rsi_exit = trial.suggest_int("rsi_exit", 60, 80)
    macd_fast = trial.suggest_int("macd_fast", 5, 20)  # shorter EMA for quick signals
    macd_slow = trial.suggest_int("macd_slow", 15, 50)  # slower EMA, must be > fast
    macd_signal = trial.suggest_int(
        "macd_signal", 5, 20
    )  # wider smoothing possibilities
    # bb_period = trial.suggest_int("bb_period", 15, 25)
    # bb_mult = trial.suggest_float("bb_mult", 1.5, 2.5)
    # adx_period = trial.suggest_int("adx_period", 10, 20)
    # adx_thresh = trial.suggest_float("adx_thresh", 15, 30)
    # atr_period = trial.suggest_int("atr_period", 10, 20)
    # atr_ma_period = trial.suggest_int("atr_ma_period", 2, 5)
    # atr_trail_mult = trial.suggest_float("atr_trail_mult", 1.0, 3.0)
    trend_sma_period = trial.suggest_int(
        "trend_sma_period", 10, 300
    )  # from short trend to 1-year

    if fast >= slow or macd_fast >= macd_slow:
        return -9999

    final_balance, win_rate, profit_factor, max_drawdown, trades, returns = (
        backtest_advanced(
            df_1h,
            df_1d,
            fast,
            slow,
            rsi_period,
            rsi_threshold,
            macd_fast,
            macd_slow,
            macd_signal,
            trend_sma_period,
            # atr_period,
            # atr_ma_period,
            # atr_trail_mult,
            mode=None,
        )
    )

    # Old option
    # score = (final_balance - 2000) \
    #         + (profit_factor * 500) \
    #         + (win_rate * 1000) \
    #         - (max_drawdown * 2000)

    # Option 1
    # score = (
    #     (final_balance - INITIAL_BALANCE)
    #     - (max_drawdown * 3)
    #     + (win_rate * 200 if len(trades) > 5 else 0)
    # )

    # Option 2
    score = (final_balance - INITIAL_BALANCE) / (
        1 + max_drawdown + 1 / (1 + profit_factor)
    ) + (win_rate * 100 if len(trades) > 5 else 0)

    # TODO improve this option optimization
    # Option 3: prioritize risk-adjusted return + penalize drawdown + reward consistency
    # sharpe_like = 0
    # if len(returns) > 0:
    #     sharpe_like = np.mean(returns) / (np.std(returns) + 1e-9)
    # score = (
    #     sharpe_like * 300
    #     + (profit_factor * 150)
    #     + (final_balance - INITIAL_BALANCE) * 0.01
    #     - (max_drawdown * 0.5)
    # )

    return score


# --- Launch Optimization ---
study = optuna.create_study(direction="maximize")
study.optimize(objective, n_trials=1000, n_jobs=-1)

# --- Results ---
print("\nBest Parameters Found:")
print(study.best_params)
print(f"Best score: {study.best_value:.2f}")

# Save study to csv
df_study = study.trials_dataframe()
df_study.to_csv(
    OPTI_DIR.joinpath("optuna_mas_optimization_5_bullish_trend_score_option_3.csv"),
    index=False,
)
