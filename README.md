# Install

```bash
pip install -e .
```

# Improvements

| Strategy            | Indicators Used                   | Strengths                          | Weaknesses                                        |
| ------------------- | --------------------------------- | ---------------------------------- | ------------------------------------------------- |
| MACD Strategy       | MACD, RSI                         | Great for trend changes + momentum | Can lag in ranging markets                        |
| RSI Strategy        | RSI, EMA                          | Good oversold/overbought logic     | Needs volatility to shine                         |
| Stochastic Strategy | Stochastic, RSI                   | Tight entries in oversold zones    | Can give false signals without trend confirmation |
| TEMA/DEMA Strategy  | TEMA (fast/slow), DEMA, Stop Loss | Momentum + MA crossover            | Smoother but still susceptible to chop            |

# Profit Factor Analysis

| Profit Factor | Meaning                                                                 |
| ------------- | ----------------------------------------------------------------------- |
| < 1.0         | Losing strategy — you lose more than you gain                           |
| = 1.0         | Break-even — barely compensates for losses                              |
| 1.1 - 1.5     | Weak edge — may not hold up after slippage, fees, market noise          |
| 1.5 - 2.0     | Decent edge — strategy may be viable with low costs                     |
| 2.0 - 3.0     | Strong edge — good risk-adjusted returns                                |
| > 3.0         | Exceptional — great risk-reward ratio, possibly underutilized potential |

# Count-Based Win Rate (% of trades won)

| Win Rate | Interpretation                                                    | Example Strategy Type      |
| -------- | ----------------------------------------------------------------- | -------------------------- |
| < 40%    | Likely a trend-following system with large wins                   | Trend Following, Breakouts |
| 40–60%   | Balanced system, needs decent risk-reward                         | Momentum or Swing Systems  |
| > 60%    | High-probability setups, but may have smaller profits             | Mean Reversion, Scalping   |
| > 80%    | Often overfitted or low-RR scalping strategies — handle with care | Grid Bots, Market Making   |

# PnL-Based Win Rate (Profit Contribution)

| PnL-Based Win Rate | Interpretation                                                    | Health Check             |
| ------------------ | ----------------------------------------------------------------- | ------------------------ |
| < 40%              | Losses are eating into gains — strategy likely unsustainable      | Red flag                 |
| 40–60%             | Needs improvement — watch slippage and reward:risk ratio          | Meh                      |
| 60–75%             | Good — profitable wins outweigh the damage from losses            | Healthy                  |
| > 75%              | Excellent — strong risk management + edge in entries/exits        | Very strong edge         |
| > 90%              | Likely a low-frequency sniper system or high-RR breakout strategy | May be rare but powerful |
