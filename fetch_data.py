from pathlib import Path

import ccxt
import pandas as pd

CURRENT_DIR = Path(__file__).parent
DATA_DIR = CURRENT_DIR.joinpath("backtest", "data")

SYMBOL = "BTC/USDT"
TIMEFRAME = "1h"

ohlcv = []
limit = 1000
init_date = pd.Timestamp("2017-01-01")
today = pd.Timestamp.today()
exchange = ccxt.binance()
while init_date < today:
    ohlcv += exchange.fetch_ohlcv(
        SYMBOL, since=init_date.value // 10**6, limit=limit, timeframe=TIMEFRAME
    )
    init_date += pd.Timedelta(1000, TIMEFRAME[-1])

df = pd.DataFrame(
    ohlcv, columns=["timestamp", "open", "high", "low", "close", "volume"]
)
df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
df.set_index("timestamp", inplace=True)
df = df.drop_duplicates()
if df.index.duplicated().any():
    print(f"There are duplicated dates {df[df.index.duplicated()]}")
df.to_csv(DATA_DIR.joinpath(f"{SYMBOL.replace('/', '')}_{TIMEFRAME}.csv"))
