import ccxt
import pandas as pd
import pandas_ta as ta
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split, GridSearchCV, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import classification_report, roc_auc_score
import numpy as np

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

# Drop NaNs and define features and target
df_ml = df.dropna().copy()
df_ml["future_return"] = df_ml["close"].pct_change(periods=6).shift(-6)
df_ml["target"] = (df_ml["future_return"] > 0).astype(int)

features = ["RSI", "EMA", "ATR", "ATR_MA", "ADX", "BBW", "BBW_SMA"]
X = df_ml[features]
y = df_ml["target"]

# Train/Test Split
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# Hyperparameter Grid
param_grid = {
    "n_estimators": [100, 200],
    "max_depth": [3, 5, 10],
    "min_samples_split": [2, 5],
    "min_samples_leaf": [1, 2],
}

# Grid Search with Cross-Validation
rf = RandomForestClassifier(random_state=42)
grid_search = GridSearchCV(rf, param_grid, cv=5, scoring='f1', verbose=1)
grid_search.fit(X_train, y_train)

# Best model
best_model = grid_search.best_estimator_

# Evaluation
y_pred = best_model.predict(X_test)
y_proba = best_model.predict_proba(X_test)[:, 1]

print("\n🔍 Classification Report:")
print(classification_report(y_test, y_pred))

print(f"🎯 AUC-ROC Score: {roc_auc_score(y_test, y_proba):.2f}")

# Optional: Cross-validation score
cv_scores = cross_val_score(best_model, X, y, cv=5, scoring='f1')
print(f"📊 Cross-Validation F1 Scores: {cv_scores}")
print(f"Mean F1 Score: {np.mean(cv_scores):.3f}")

# ----- ML-Based Backtest -----

position = False
entry_price = 0
stop_loss_price = 0
balance = INITIAL_BALANCE
units = 0
ml_trades = []

# Align DataFrame with trained model
df_bt = df_ml.loc[X_test.index].copy()

for i in range(len(df_bt)):
    row = df_bt.iloc[i]
    X_row = row[features].values.reshape(1, -1)
    prob_up = best_model.predict_proba(X_row)[0][1]

    # ENTRY: ML predicts high chance of price increase
    if not position and prob_up > 0.6:
        entry_price = row["close"]
        stop_loss_price = entry_price * (1 - STOP_LOSS_PCT)
        units = balance / entry_price
        entry_time = row.name
        position = True
        print(f"[ML ENTRY] {entry_time} @ {entry_price:.2f} | Prob: {prob_up:.2f}")

    # EXIT: Hit stop loss or prediction flips bearish
    elif position:
        price = row["close"]
        prob_down = best_model.predict_proba(X_row)[0][0]
        stop_hit = price <= stop_loss_price

        if stop_hit or prob_down > 0.55:  # or prob_up < 0.5:
            sell_balance = units * price
            position = False
            exit_time = row.name
            print(f"[ML EXIT] {exit_time} @ {price:.2f}")
            ml_trades.append({
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

# ----- Results -----
print(f"\n💰 Final ML Balance: ${balance:.2f}")
if ml_trades:
    ml_df = pd.DataFrame(ml_trades)
    print("\n📋 ML Trade Summary:")
    print(ml_df)

    # Plot
    plt.figure(figsize=(14, 6))
    plt.plot(df["close"], label="Close Price", alpha=0.7)
    for trade in ml_trades:
        plt.axvline(trade["entry_time"], color="green", linestyle="--", alpha=0.6)
        plt.axvline(trade["exit_time"], color="red", linestyle="--", alpha=0.6)
    plt.title("ML-Driven Strategy Backtest")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig("images/ml_backtest")
