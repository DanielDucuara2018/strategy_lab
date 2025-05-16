import pandas as pd
from pathlib import Path

CURRENT_DIR = Path(__file__).parent
DATA_DIR = CURRENT_DIR.joinpath("backtest", "data")

# Load your original hourly data
btc_1h = pd.read_csv(DATA_DIR.joinpath("BTCUSDT_1h.csv"))
btc_1h["timestamp"] = pd.to_datetime(btc_1h["timestamp"])
btc_1h = btc_1h.set_index("timestamp")

# Reindex to a perfect 1-hour frequency (fill missing hours if any)
btc_1h = btc_1h.asfreq("1h")

# Remove rows with NaNs (in case some missing candles appeared)
btc_1h = btc_1h.dropna()

# Save clean file
btc_1h.to_csv(DATA_DIR.joinpath("BTCUSDT_1h_cleaned.csv"))

print(
    f"Hourly BTC data synced: {btc_1h.shape[0]} rows from {btc_1h.index.min()} to {btc_1h.index.max()}"
)


# Load your original daily data
btc_1d = pd.read_csv(DATA_DIR.joinpath("BTCUSDT_1d.csv"))
btc_1d["timestamp"] = pd.to_datetime(btc_1d["timestamp"])
btc_1d = btc_1d.set_index("timestamp")

# Reindex to a perfect 1-day frequency (fill missing days if any)
btc_1d = btc_1d.asfreq("1d")

# Remove rows with NaNs
btc_1d = btc_1d.dropna()

# Save clean file
btc_1d.to_csv(DATA_DIR.joinpath("BTCUSDT_1d_cleaned.csv"))

print(
    f"Daily BTC data synced: {btc_1d.shape[0]} rows from {btc_1d.index.min()} to {btc_1d.index.max()}"
)
