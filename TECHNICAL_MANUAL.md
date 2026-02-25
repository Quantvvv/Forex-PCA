# Technical Manual: Forex PCA Statistical Arbitrage Strategy

## Quick Overview

The **Forex PCA Statistical Arbitrage** strategy identifies and trades temporary deviations between currency pairs and benchmark instruments. When a pair deviates significantly from its historical relationship with a benchmark (e.g., DXY, Gold), the strategy assumes the deviation is temporary and profits from the reversion.


The higher the timeframe, the more stable the strategy, but one limitation: the number of trades drops significantly. It's important to note that when changing the timeframe, entry/exit boundaries should also be adjusted due to the different influence of the Z window.
---

## Strategy Concept

### How It Works

1. **Establish baseline:** Regression model relationship between pair and benchmark
2. **Detect anomaly:** When pair deviates 2+ standard deviations from expected value
3. **Validate reversion:** ADF test confirms spread will mean-revert (p-value < 0.05)
4. **Enter trade:** Buy undervalued, sell overvalued
5. **Exit:** When spread reverts or stop loss hits

### Mathematical Foundation

**Regression Model:**
$$\log P_t = \alpha + \beta \cdot \log B_t + \epsilon_t$$

- $\epsilon_t$ = spread (pair deviation from expected value)
- Uses rolling 50-candle window (adapts to market regimes)

**Z-Score Normalization:**
$$Z = \frac{\text{spread} - \text{mean}}{\text{std deviation}}$$

- $Z = -2$ → significant undervaluation (BUY)
- $Z = +2$ → significant overvaluation (SELL)

**Stationarity Test (ADF):**
- p-value < 0.05 → Spread reverts to mean ✅ (trade it)
- p-value > 0.05 → Spread may trend → Skip entry

---

## Signal Generation

### Entry Modes

**Standard (Recommended):**
- Enter when Z crosses -2.0 (long) or +2.0 (short)
- Exit when Z crosses 1.5 / -1.5
- Simple, proven, no look-ahead bias

**Wick Mode:**
- Enter when previous candle's high/low touches trigger level
- Faster entries, higher frequency, more false signals

### Entry Process

1. Calculate spread based on current regression
2. Convert spread to Z-score
3. Run ADF test on spread (check for stationarity)
4. IF Z crosses threshold AND ADF p-value ≤ 0.05:
   - **ENTER** trade at current candle close

---

## Risk Management

### Position Sizing

**Capital allocation (always enabled):**
- Each position's PnL divided by concurrent position count
- Reflects realistic account constraints
- Prevents artificial inflation from overlapping trades

Example: 3 positions on $10K account
- Trade A: +5% → weighted to +1.67%
- Trade B: -2% → weighted to -0.67%
- Total equity impact: +1.0% (realistic)

### Position Limits

| Parameter | Default | Purpose |
|-----------|---------|---------|
| **Max Concurrent** | 200 | Total portfolio exposure cap |
| **Max Per Pair** | 5 | Prevents over-concentration; allows pyramiding |
| **Stop Loss** | 0.5% | Exit losing positions quickly |
| **Cooldown** | 1 candle | Prevents whipsaw re-entries |


---

## Configuration Guide

### Benchmark Selection

| Benchmark | When to Use | Characteristics |
|-----------|------------|-----------------|
| **DXY** | General USD strength | Most stable, inverse with most pairs |
| **Gold** | Risk sentiment | Good for commodity-linked pairs (CAD, AUD) |
| **Oil** | Energy demand | Petrocurrency correlation |

### Key Parameters

**Entry Z-Scores:**
- **-2.0 / +2.0** (DEFAULT) - Balanced, proven stable
- **-2.5 / +2.5** - Conservative, fewer signals
- **-1.5 / +1.5** - Aggressive, more trades

**Regression Window:**
- **50 candles** (DEFAULT) - Best balance
- **30** - Faster, noisier
- **100** - Smoother, slower

From practice, the optimal values ​​are only 50-60

**ADF Threshold:**
- **0.05** (DEFAULT) - Strict, high quality
- **0.10** - Looser, more trades

### Quick Optimization

**For more trades:** Threshold -2.0, ADF 0.10,
**For quality:** Threshold -2.5, ADF 0.01,
**For safety:** Lower max concurrent, tighter stop loss

---

## Troubleshooting

| Issue | Solutions |
|--------|-----------|
| **No trades** | Lower Z threshold; change benchmark; add data |
| **All p-values > 0.05** | change benchmark; loosen ADF threshold |
| **Too slow** | Reduce lookback days; use longer timeframe; fewer pairs |
| **Download fails** | Check internet; verify pair names;|
| **Too much drawdown** | Reduce max concurrent; tighter stop loss; choose a higher time frame |

---

## Implementation Notes

### Backtesting Integrity

- ✅ No future data used in signals
- ✅ ADF computed from historical data only
- ✅ Commission included in all trades
- ✅ Last unclosed candle removed

### Key Assumptions

- Execution at candle close (realistic for FX)
- Dukascopy data reliable (very few gaps in major pairs)
- Constant beta (rolling window mitigates)
- No market impact (true for retail size)

### Optimization Best Practices

**Safe:**
- Parameter sweep on 50% data, test on 50%
- Portfolio-level optimization (position limits)

**Avoid (overfitting):**
- Per-pair optimization on full historical set
- Over-tuning parameters on single regime

### Strategy Limitations

- ❌ Regime-dependent (broken correlations)
- ❌ No black swan protection
- ❌ Overnight risk not modeled
- ❌ Degrades in high-volatility environments

### When to Use

- ✅ Normal market conditions
- ✅ As component of diversified system
- ✅ Systematic, rules-based trading

### When NOT to Use

- ❌ Standalone live strategy (without risk controls)
- ❌ During major news events

