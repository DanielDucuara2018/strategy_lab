import ccxt
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report

# Parameters
RSI_PERIOD = 2
EMA_PERIOD = 200
ADX_PERIOD = 14
ATR_PERIOD = 14
BBW_PERIOD = 20
STOP_LOSS_PCT = 0.10
INITIAL_BALANCE = 2000

# Load data
ohlcv = []
limit = 1000
init_date = pd.Timestamp("2017-01-01")
today = pd.Timestamp.today()
exchange = ccxt.binance()
while init_date < today:
    ohlcv += exchange.fetch_ohlcv('BTC/USDT', since=init_date.value // 10**6, limit=limit, timeframe='1h')
    init_date += pd.Timedelta(1000, "h")

# DataFrame setup
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']).drop_duplicates()
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# Indicators
df["RSI"] = ta.rsi(df["close"], length=RSI_PERIOD)
df["EMA"] = ta.ema(df["close"], length=EMA_PERIOD)
df["ATR"] = ta.atr(df["high"], df["low"], df["close"], length=ATR_PERIOD)
df["ATR_MA"] = df["ATR"].rolling(20).mean()
df["ADX"] = ta.adx(df["high"], df["low"], df["close"], length=ADX_PERIOD)[f"ADX_{ADX_PERIOD}"]
bb = ta.bbands(df["close"], length=BBW_PERIOD)
df["BBW"] = (bb[f"BBU_{BBW_PERIOD}_2.0"] - bb[f"BBL_{BBW_PERIOD}_2.0"]) / df["close"]
df["BBW_SMA"] = df["BBW"].rolling(20).mean()
df["return_1h"] = df["close"].pct_change(1)
df["future_return"] = df["close"].shift(-6) / df["close"] - 1

df.dropna(inplace=True)
df["target"] = (df["future_return"] > 0.01).astype(int)

# ML Training
features = ["RSI", "EMA", "ATR", "ATR_MA", "ADX", "BBW", "BBW_SMA", "return_1h"]
X = df[features]
y = df["target"]
X_train, X_test, y_train, y_test = train_test_split(X, y, shuffle=False, test_size=0.2)

model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
model.fit(X_train, y_train)
print(classification_report(y_test, model.predict(X_test)))

# Prediction
df["prediction"] = model.predict(X)

# Backtest
position = False
entry_price = 0
stop_loss_price = 0
balance = INITIAL_BALANCE
units = 0
trades = []

for i in range(1, len(df)):
    row = df.iloc[i]
    if not position and row["prediction"] == 1:
        entry_price = row["close"]
        stop_loss_price = entry_price * (1 - STOP_LOSS_PCT)
        units = balance / entry_price
        position = True
        entry_time = row.name
        print(f"[ENTRY] {entry_time} @ {entry_price:.2f}")
    elif position:
        price = row["close"]
        stop_hit = price <= stop_loss_price
        if stop_hit:
            sell_balance = units * price
            position = False
            exit_time = row.name
            print(f"[EXIT] {exit_time} @ {price:.2f}")
            trades.append({
                "entry_time": entry_time,
                "exit_time": exit_time,
                "entry_price": entry_price,
                "exit_price": price,
                "pnl": sell_balance - balance,
                "return_pct": (price - entry_price) / entry_price * 100,
                "old_balance": balance,
                "new_balance": sell_balance
            })
            balance = sell_balance

# Results
print(f"\nFinal Balance: ${balance:.2f}")
if trades:
    trade_df = pd.DataFrame(trades)
    print(trade_df)

    plt.figure(figsize=(14, 6))
    plt.plot(df["close"], label="Close Price", alpha=0.7)
    for trade in trades:
        plt.axvline(trade["entry_time"], color="green", linestyle="--", alpha=0.6)
        plt.axvline(trade["exit_time"], color="red", linestyle="--", alpha=0.6)
    plt.title("ML-Driven Strategy Backtest")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig("rsi_ml_strategy")
