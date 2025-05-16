from pathlib import Path

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from moving_average_spread_strategy import (
    INITIAL_BALANCE,
    SYMBOL,
    TIMEFRAME_1D,
    TIMEFRAME_1H,
    backtest_advanced,
    get_data,
)

CURRENT_DIR = Path(__file__).parent
IMAGES_DIR = CURRENT_DIR.joinpath("images")

df_1h = get_data(SYMBOL, TIMEFRAME_1H)
df_1d = get_data(SYMBOL, TIMEFRAME_1D)

final_balance, win_rate, profit_factor, max_drawdown, trades, returns = (
    backtest_advanced(
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
        # **{'fast': 14, 'slow': 49, 'rsi_period': 24, 'rsi_threshold': 66, 'macd_fast': 16, 'macd_slow': 24, 'macd_signal': 5, 'trend_sma_period': 10}
        # **{'fast': 9, 'slow': 39, 'rsi_period': 19, 'rsi_threshold': 68, 'macd_fast': 11, 'macd_slow': 22, 'macd_signal': 8, 'trend_sma_period': 10}
        # **{'fast': 15, 'slow': 48, 'rsi_period': 27, 'rsi_threshold': 63, 'macd_fast': 7, 'macd_slow': 44, 'macd_signal': 13, 'trend_sma_period': 10}
        # **{'fast': 14, 'slow': 49, 'rsi_period': 22, 'rsi_threshold': 65, 'macd_fast': 8, 'macd_slow': 31, 'macd_signal': 10, 'trend_sma_period': 10}
        # RSI_PERIOD,
        # RSI_THRESHOLD,
        # MACD_FAST,
        # MACD_SLOW,
        # MACD_SIGNAL,
        # ATR_PERIOD,
        # ATR_MA_PERIOD,
        # ATR_TRAIL_MULTIPLIER
    )
)
# --- Results ---
print(f"\nFinal Balance: ${final_balance:.2f}")

if trades:
    trade_df = pd.DataFrame(trades)
    print("\nTrade Summary:")
    print(trade_df)

    # Performance Metrics
    wins = trade_df[trade_df["pnl"] > 0]
    losses = trade_df[trade_df["pnl"] <= 0]
    total_wins = wins["pnl"].sum()
    total_losses = abs(losses["pnl"].sum())
    value_weighted_win_rate = (
        total_wins / (total_wins + total_losses) * 100
        if (total_wins + total_losses) > 0
        else 0
    )
    win_rate = len(wins) / len(trade_df) * 100
    profit_factor = total_wins / total_losses if total_losses != 0 else float("inf")
    max_drawdown = (trade_df["pnl"].cumsum().cummax() - trade_df["pnl"].cumsum()).max()
    total_pnl = trade_df["pnl"].sum()
    sharpe_like = float("nan")
    if len(returns) > 0:
        sharpe_like = np.mean(returns) / (np.std(returns) + 1e-9)  # avoid div by zero

    print("\nStats:")
    print(f"Total Trades: {len(trade_df)}")
    print(f"Win Trades: {len(wins)}")
    print(f"Lose Trades: {len(losses)}")
    print(f"Max win: ${wins['pnl'].max():.2f}")
    print(f"Max lose: ${losses['pnl'].min():.2f}")
    print(f"Win Rate (Count-Based): {win_rate:.2f}%")
    print(f"Win Rate (PnL-Weighted): {value_weighted_win_rate:.2f}%")
    print(f"Profit Factor: {profit_factor:.2f}")
    print(f"Sharpe-like Ratio (return_pct/std): {sharpe_like:.2f}")
    print(f"Max Drawdown: ${max_drawdown:.2f}")
    print(f"Total PnL: ${total_pnl:.2f}")
    print(f"Final Balance: ${(total_pnl + INITIAL_BALANCE):.2f}")

    # Plot
    plt.figure(figsize=(14, 6))
    plt.plot(df_1h["close"], label="Close Price", alpha=0.7)
    for trade in trades:
        plt.axvline(trade["entry_time"], color="green", linestyle="--", alpha=0.6)
        plt.axvline(trade["exit_time"], color="red", linestyle="--", alpha=0.6)
    plt.title("MAS (Moving Average Spread) Strategy Backtest")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(IMAGES_DIR.joinpath(f"{SYMBOL.replace('/', '')}_mas_strategy"))

    # --- Plot Equity Curve ---
    plt.figure(figsize=(12, 6))
    plt.plot(trade_df["old_balance"])
    plt.title("MAS (Moving Average Spread) Strategy Equity Curve")
    plt.xlabel("Trades")
    plt.ylabel("Balance")
    plt.grid(True)
    plt.tight_layout()
    plt.savefig(IMAGES_DIR.joinpath(f"{SYMBOL.replace('/', '')}_mas_equity_curve.png"))
