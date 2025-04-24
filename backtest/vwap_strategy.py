import ccxt
import pandas as pd
import matplotlib.pyplot as plt
import mplfinance as mpf
from datetime import datetime

# Fetch historical 10-minute data for 2 days (~300 candles)
exchange = ccxt.binance()
ohlcv = exchange.fetch_ohlcv('BTC/USDT', timeframe='5m', limit=600)

# DataFrame setup
df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
df.set_index('timestamp', inplace=True)

# VWAP calculation
df['pv'] = df['close'] * df['volume']
df['cumulative_pv'] = df['pv'].cumsum()
df['cumulative_volume'] = df['volume'].cumsum()
df['vwap'] = df['cumulative_pv'] / df['cumulative_volume']

# Standard deviation and VWAP bands
df['std'] = df['close'].rolling(window=20).std()
df['vwap_upper_1SD'] = df['vwap'] + 1 * df['std']
df['vwap_lower_1SD'] = df['vwap'] - 1 * df['std']
df['vwap_upper_2SD'] = df['vwap'] + 2 * df['std']
df['vwap_lower_2SD'] = df['vwap'] - 2 * df['std']

# Yesterday's VWAP (used as fixed S/R level)
df['date'] = df.index.date
yesterday = df['date'].unique()[-2]
vwap_yesterday = df[df['date'] == yesterday]['vwap'].iloc[-1]
df['vwap_yesterday'] = vwap_yesterday

# Simulated short entry strategy
entries = {}
exits = {}

entry_price = None
stop_loss = None
take_profit = None
entry_index = None

for i in range(1, len(df)):
    # Check for entry
    if (
        df['close'].iloc[i - 1] > df['vwap'].iloc[i - 1] and
        df['close'].iloc[i] < df['vwap'].iloc[i] and
        df['close'].iloc[i] < vwap_yesterday and
        entry_price is None
    ):
        entry_price = df['close'].iloc[i]
        stop_loss = df['vwap_upper_1SD'].iloc[i]
        take_profit = df['vwap_lower_2SD'].iloc[i]
        entry_index = df.index[i]

    # Check for exit (if in a position)
    elif entry_price is not None:
        if df['high'].iloc[i] >= stop_loss:
            exit_price = stop_loss
            exit_index = df.index[i]
        elif df['low'].iloc[i] <= take_profit:
            exit_price = take_profit
            exit_index = df.index[i]
        else:
            continue  # keep holding

        # Save entry and exit
        entries[entry_index] = entry_price
        exits[exit_index] = exit_price
 
        # Reset
        entry_price = None
        stop_loss = None
        take_profit = None
        entry_index = None

# Plot chart with entry/exit and VWAP levels
addplots = [
    mpf.make_addplot(df['vwap'], color='purple', width=1.2),
    mpf.make_addplot(df['vwap_upper_1SD'], color='gray', linestyle='dashed'),
    mpf.make_addplot(df['vwap_lower_1SD'], color='yellow', linestyle='dashed'),
    mpf.make_addplot(df['vwap_upper_2SD'], color='green', linestyle='dashed'),
    mpf.make_addplot(df['vwap_lower_2SD'], color='red', linestyle='dashed'),
    mpf.make_addplot(df['vwap_yesterday'], color='orange', linestyle='dashdot'),
]

fig, axes = mpf.plot(
    df,
    type='candle',
    addplot=addplots,
    volume=True,
    returnfig=True,
    style='charles',
    title='VWAP Strategy with ±2 SD and Yesterday VWAP',
)

# Draw trade entry/exit
ax = axes[0]
for entry in entries:
    ax.axvline(entry, color='blue', linestyle='--', label='Entry')
for exit in exits:
    ax.axvline(exit, color='red', linestyle='--', label='Exit')

# Avoid duplicate labels
handles, labels = ax.get_legend_handles_labels()
unique_labels = dict(zip(labels, handles))
ax.legend(unique_labels.values(), unique_labels.keys())

# Save the chart
fig.savefig('images/vwap_strategy_trade.png')
print("Chart saved as vwap_strategy_trade.png")