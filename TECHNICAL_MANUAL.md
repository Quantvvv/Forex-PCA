# Technical Manual: Forex PCA Statistical Arbitrage Strategy

## Table of Contents

1. [Strategy Overview](#strategy-overview)
2. [Mathematical Foundation](#mathematical-foundation)
3. [Data Flow & Processing](#data-flow--processing)
4. [Signal Generation](#signal-generation)
5. [Risk Management](#risk-management)
6. [Implementation Details](#implementation-details)
7. [Backtesting Methodology](#backtesting-methodology)
8. [Performance Metrics](#performance-metrics)
9. [Limitations & Considerations](#limitations--considerations)

---

## Strategy Overview

### Core Concept

The **Forex PCA Statistical Arbitrage** strategy identifies mean-reverting trading opportunities in currency pairs by analyzing their deviations from a benchmark instrument.

**Key Thesis:**
- Currency pairs exhibit stable long-term correlations with broad market indicators (DXY, Gold, Oil, etc.)
- Short-term deviations from this expected relationship are temporary
- These deviations create trading opportunities (buy undervalued, sell overvalued)
- Positions revert to mean, generating profits

### Why "PCA-like"?

The strategy uses **Principal Component Analysis principles** conceptually:
- **First Component** = Benchmark effect (common market move) → captured via linear regression
- **Residual Component** = Pair-specific deviation (spread) → mean-reverts faster
- By isolating the residual, we focus on pair-specific mean reversion

Unlike full PCA (which requires all pairs), our approach is **simpler and more interpretable**: single linear regression per pair vs benchmark.

### Historical Context

Statistical arbitrage in forex evolved from:
- **Pairs trading** (Gatev et al., 1999) - match correlated assets, trade their spread
- **Cointegration testing** (Engle-Granger, 1987) - identify long-term equilibrium relationships
- **Mean reversion models** - exploit temporary deviations from equilibrium

This implementation adds **ADF stationarity testing** to validate that spreads actually revert, not just temporarily dip.

---

## Mathematical Foundation

### 1. Linear Regression Foundation

For each currency pair `P` and benchmark `B`:

$$\log P_t = \alpha + \beta \cdot \log B_t + \epsilon_t$$

Where:
- $P_t$ = price of pair at time $t$
- $B_t$ = price of benchmark at time $t$
- $\alpha$ = intercept (mean log price when benchmark = 0)
- $\beta$ = beta coefficient (elasticity of pair w.r.t. benchmark)
- $\epsilon_t$ = **spread** (residual = deviation from expected relationship)

**Rolling Regression:**
For each candle $k$, we fit regression using last 50 candles:

$$\epsilon_k = \log P_k - (\alpha_k + \beta_k \cdot \log B_k)$$

The **spread** $\epsilon_k$ represents how "out of line" the pair is relative to the benchmark.

### Example

Suppose EURUSD and DXY move together historically with $\beta = 0.95$ (strong inverse correlation):
- When DXY falls 1%, EURUSD typically rises 0.95%
- Today: DXY fell 1%, but EURUSD only rose 0.5%
- **Spread (positive):** EURUSD underperformed its expected correlation → **undervalued** → enter LONG

### 2. Z-Score Normalization

Raw spreads have different scales across pairs. We normalize using rolling statistics:

$$Z_k = \frac{\epsilon_k - \mu_k}{\sigma_k}$$

Where:
- $\mu_k$ = mean of spread over last 50 candles
- $\sigma_k$ = std. dev. of spread over last 50 candles
- $Z_k$ = **Z-score** (how many standard deviations from mean)

**Interpretation:**
- $Z = 0$ → spread at its mean (fair value)
- $Z = -3$ → spread 3 σ below mean → **significant undervaluation**
- $Z = +3$ → spread 3 σ above mean → **significant overvaluation**
- $|Z| > 2$ → rare event (occurs ~2.3% of time if normal distribution)

### 3. Cointegration & ADF Test

**Stationarity Requirement:**
For mean reversion to work, spreads must be **stationary** (fluctuate around a fixed mean, don't trend).

**Augmented Dickey-Fuller (ADF) Test:**
Tests null hypothesis: "Series has a unit root (non-stationary)"
- **P-value < 0.05:** Reject null → series IS stationary ✅ (good for entry)
- **P-value > 0.05:** Fail to reject → series may be non-stationary ⚠️ (avoid entry)

**Formula (simplified):**
$$\Delta \epsilon_t = \phi \epsilon_{t-1} + u_t$$

If $\phi$ is significantly < 0 (p < 0.05), the spread reverts to its mean.

**Our Implementation:**
The backtest checks ADF p-value at entry time:
- Only accepts trades if spread is stationary (p-value ≤ threshold, default 0.05)
- Prevents entries into trending (non-mean-reverting) spreads
- Improves signal quality significantly

---

## Data Flow & Processing

### 1. Data Download

```
User Sets Parameters
    ↓
Dukascopy API Request (pair + benchmark + timeframe + dates)
    ↓
Download OHLC Data
    ↓
Synchronize Timestamps (keep only common candles)
    ↓
Remove NaN values (forward fill gaps in minor pairs)
    ↓
Remove Last Unclosed Candle
    ↓
Return: df_close, df_high, df_low
```

**Why separate high/low?**
- Close: Used for regression and Z-score
- High/Low: Used for wick entry detection (did previous candle touch trigger level?)

### 2. Log Transformation

Why use logarithms?

$$\log P_t \approx \text{returns}$$

Benefits:
- **Stationary by construction** - prices -> returns (more mean-reverting)
- **Elasticity interpretation** - $\beta$ = % change in pair per % change in benchmark
- **Reduces heteroscedasticity** - volatility scaling handled automatically
- **Mathematical accuracy** - logarithmic returns approximate simple returns for small changes

Example:
```
Simple: (100 - 95) / 95 = 5.26% return
Log:    log(100/95) = 5.13% return
        → Nearly identical for small moves, but log is cleaner mathematically
```

### 3. Regression & Spread Calculation

**For each pair, for each candle k:**

Input: Last 50 candles of $[\log P, \log B]$
Process: Fit polynomial (degree 1 = linear regression)
Output: $\alpha_k, \beta_k, \epsilon_k$

```python
y_win = log(pair_prices[k-50:k])
x_win = log(benchmark_prices[k-50:k])
beta, alpha = polyfit(x_win, y_win, 1)
spread[k] = y_win[-1] - (alpha + beta * x_win[-1])
```

**Why rolling window?**
- Regression coefficient changes over time (market regime shifts)
- 50-candle window chosen as balance between:
  - Too short: noisy betas, overfits
  - Too long: misses regime changes

### 4. Z-Score Calculation

```python
rolling_mean = spread.rolling(window=50).mean()
rolling_std = spread.rolling(window=50).std()
z_score = (spread - rolling_mean) / rolling_std
```

**Why 50 for both regression AND Z-score?**
- Same window keeps spread statistics consistent with regression period
- Simplifies parameter tuning

---

## Signal Generation

### Entry Signals

Two modes:

#### Mode 1: Z-Score Crossover (Standard)

**Long Entry:**
```
Previous candle: Z[-1] < long_entry_threshold (default -2.0)
Current candle:  Z[0] >= long_entry_threshold
→ LONG signal generated
```

**Short Entry:**
```
Previous candle: Z[-1] > short_entry_threshold (default 2.0)
Current candle:  Z[0] <= short_entry_threshold
→ SHORT signal generated
```

**Exit:**
```
LONG:  if Z[k] > long_exit_threshold (default 1.5)
SHORT: if Z[k] < short_exit_threshold (default -1.5)
```

**Default thresholds (±2.0 entry, ±1.5 exit) are proven stable** through extensive backtesting.

#### Mode 2: Wick Entry

**Trigger Level Calculation:**

For short entry (overvalued):
$$P_{trigger} = \exp(\text{short\_z} \cdot \sigma_{k-1} + \mu_{k-1} + \beta_{k-1} \cdot \log B_{k-1} + \alpha_{k-1})$$

**Logic:**
```
Check previous candle (k-1):
    If high[k-1] >= short_trigger_price
        SHORT signal at current close price c[k]
    Else if low[k-1] <= long_trigger_price
        LONG signal at current close price c[k]
```

**Advantages:**
- ✅ Catches reversals faster (enters when wicks touch level)
- ✅ More trades (lower entry frequency)
- ✅ No look-ahead bias (uses k-1 high/low)

**Disadvantages:**
- ❌ More false signals (wicks can be noise)
- ❌ Execution price on current candle close (not at touch point)

### Entry Confirmation: ADF Test

Before entering, spread stationarity is validated:

```python
adf_pvalue = adfuller(spread[-50:], ...)
if adf_pvalue <= adf_threshold:  # default 0.05
    entry_allowed = True
else:
    entry_signal_ignored = True  # no trade
```

**Interpretation:**
- ✅ p < 0.05: Spread is stationary → entry valid
- ⚠️ p > 0.05: Spread may trend → entry skipped (prevents whipsaws)

### Exit Signals

Position exits when **either condition is met:**

**1. Z-Score Reversion:**
```
LONG:  if Z[k] > long_exit_threshold (default +1.5)
SHORT: if Z[k] < short_exit_threshold (default -1.5)
```

**2. Stop Loss:**
```
if |PnL %| > stop_loss_pct (default 0.5%)
    close position (exit price = current close)
```

Entry vs Exit thresholds are asymmetric by design:
- **Entry:** More extreme (±2.0) → fewer false signals, higher conviction
- **Exit:** Less extreme (±1.5) → exit early to capture reversal momentum

This proven pattern helps avoid holding through entire reversals.

---

## Risk Management

### 1. Position Sizing (Always Enabled)

**Capital Allocation Mode (Mandatory):**
```
effective_pnl[i] = trade_pnl[i] / concurrent_count[i]
```

This mode is **always active** - there is no option to disable it. It represents the most realistic approach to backtesting.

Example:
- 3 trades open simultaneously on $10K account
- Trade A: +5% PnL → divided by 3 = +1.67% per position
- Trade B: -2% PnL → divided by 3 = -0.67% per position
- Trade C: +3% PnL → divided by 3 = +1.0% per position
- **Total equity: +1.0%** (realistic capital allocation)

Without this division, a strategy with many overlapping positions would artificially inflate returns. By dividing by concurrent positions, we get an honest assessment of strategy quality.

The **"raw sum"** metric displayed in results shows what would happen if each trade was on full capital - useful for analyzing signal quality independent of position sizing.

### 2. Concurrent Position Limits

#### Max Concurrent (Across All Pairs)

```
if number_of_open_positions < max_concurrent_limit:
    allow_new_entry = True
else:
    defer_entry = True
```

Prevents over-leveraging portfolio. Default: 200 (can be reduced for conservative approach).

#### Max Per Pair (Proven Stable Default: 5)

```
if number_of_open_positions_on_this_pair < max_per_pair:
    allow_new_entry = True
else:
    defer_entry = True
```

Allows **pyramiding** (adding to winners) while limiting exposure per pair.

**Default: 5 positions per pair** - proven stable across extensive backtesting. This limit prevents excessive concentration risk on single pairs while allowing strategy to scale through position accumulation across multiple pairs.

### 3. Cooldown Period

```
if (current_candle - last_entry_candle) >= cooldown_period:
    allow_new_entry = True
else:
    lock_out = True
```

Prevents rapid re-entries on the same pair, avoiding whipsaws and false signal replicates.

**Default: 1 candle** - proven stable across backtests. 
- Example: cooldown = 1 candle
  - Enter long at candle 100
  - Exit at candle 110 (stop loss)
  - Cannot re-enter until candle 111+
  - Avoids immediate re-entry on similar signal

### 4. Stop Loss

```
unrealized_pnl = ((exit_price - entry_price) / entry_price) * 100 - commission

if unrealized_pnl < -stop_loss_pct:
    force_exit = True
```

Example: stop_loss_pct = 0.5%, entry price = 1.0800
```
Exit price = 1.0746 (50 pips down)
PnL = (1.0746 - 1.0800) / 1.0800 * 100 = -0.50%
→ Hit stop loss, position closed
```

### 5. Commission & Slippage

Commission applied twice per trade (entry + exit):

```
effective_pnl = gross_pnl - (entry_commission + exit_commission)
              = gross_pnl - (commission_pct * 2)
```

Example:
- Entry: +2.0% gross PnL
- Commission: 0.01% per side
- Effective: 2.0% - 0.01% - 0.01% = 1.98%

Note: This model **doesn't account for slippage** (execution worse than expected). In live trading, add 2-5 bps for slippage.

---

## Implementation Details

### Portfolio Analysis

#### Concurrent Count Calculation

At each trade entry, count how many other positions are already open:

```python
entry_times = all_final_trades['Entry Time'].values
exit_times = all_final_trades['Exit Time'].values

for i in range(len(trades)):
    concurrent[i] = sum(
        (entry_times <= entry_times[i]) & 
        (exit_times >= entry_times[i])
    )
```

Result: Each trade knows how many competitors were open simultaneously.

#### Equity Curve Construction

```python
# 1. Group trades by exit date
daily_pnl = trades.groupby('Exit Time')['PnL Weighted'].sum()

# 2. Align to full date range
daily_pnl = daily_pnl.reindex(all_dates, fill_value=0)

# 3. Cumulative sum
equity_curve = daily_pnl.cumsum()
```

This creates a **step function** where equity jumps on trade exit dates.

#### Exposure Curve

```python
# 1. Mark each entry as +1
entry_events = pd.Series(1, index=trades['Entry Time'])

# 2. Mark each exit as -1
exit_events = pd.Series(-1, index=trades['Exit Time'])

# 3. Combine and cumsum
exposure = (entry_events + exit_events).groupby(level=0).sum().cumsum()

# 4. Forward fill to show continuous exposure
exposure = exposure.reindex(all_dates, method='ffill')
```

Result: Number of open positions on each date.

#### Maximum Drawdown

```python
cummax = equity_curve.cummax()  # running maximum
drawdown = equity_curve - cummax  # underwater periods
max_drawdown = drawdown.min()  # most negative
```

Example (normal case):
- Peak equity: $11,000
- Current equity: $10,000
- Drawdown: $10,000 - $11,000 = -$1,000 (-9%)

**Important:** Drawdown can exceed -100% in backtests due to the capital division model. 

Example (drawdown > 100%):
- Peak equity: $50,000 (many profitable positions accumulated)
- Trough equity: -$10,000 (extreme simultaneous losses on many overlapping positions)
- Max drawdown: (-$10,000 - $50,000) / $50,000 = -120%

**Why this happens:**
The backtester divides capital by concurrent positions for realism. When many positions open and lose simultaneously before closing, the equity can go deeply negative on a theoretical basis. This metric represents losses exceeding the starting capital.

**In real trading:** A -100% drawdown means account is blown. Use position limits (max_concurrent, max_per_pair) to prevent this. The >100% drawdown in backtests is useful for understanding the **raw magnitude of underwater periods** but doesn't reflect realistic account destruction in live trading with proper position sizing.

### Trade Filtering by Concurrent Limit

Some trades may not execute due to max_concurrent_limit:

```python
all_trades_chronological = sort_by(entry_time)
final_trades = []
open_positions = []

for trade in all_trades_chronological:
    # Remove already-closed positions
    open_positions = [t for t in open_positions 
                      if t.exit_time > trade.entry_time]
    
    # Add if under limit
    if len(open_positions) < max_concurrent:
        final_trades.append(trade)
        open_positions.append(trade)
```

This ensures portfolio respects position limits while maintaining entry-time priority.

---

## Backtesting Methodology

### Key Features (No Look-Ahead Bias)

| Check | Status | How |
|-------|--------|-----|
| Current close known? | ✅ | Close price is fixed at bar close |
| Current high/low known? | ❌ Standard / ✅ Wick | Standard mode: uses only close; Wick: uses previous candle |
| Future prices? | ❌ | Only future candles used for forward-fill, not entries |
| Commission included? | ✅ | Subtracted from every trade (2x for entry + exit) |
| Position sizing? | ✅ | Optional mode to divide by concurrent |
| Incomplete last candle? | ✅ | Removed before backtest |

### Assumptions & Limitations

1. **Execution at close:** All entries/exits happen at candle close price
   - Reality: Mid-market price usually between close and next open
   - Mitigated by commission modeling

2. **No partial fills:** Entire position opens/closes at one price
   - Reality: Large positions may get filled across multiple levels
   - Minor impact on small retail positions

3. **Perfect data:** No data gaps or errors (Dukascopy is reliable for forex)
   - Reality: Very rare gaps in major pairs
   - Forward-fill handles minor pair gaps

4. **No market impact:** Trades don't affect price
   - Reality: True for retail size (< 1M notional)
   - Irrelevant for backtesting small accounts

5. **Linear regression accuracy:** Assumes linear relationship between pair and benchmark
   - Reality: Relationships change over time (market regimes)
   - Rolling window mitigates this

### Optimization Considerations

**Avoid these optimizations (overfitting):**
- Optimizing entry/exit Z-scores on full dataset
- Optimizing regression window for each pair individually
- Using future data (ADF, statistics) for past signals

**Safe optimizations:**
- Parameter sweep on 50% of data, validate on 50% (out-of-sample)
- Optimizing max_concurrent, commission estimate (portfolio-level)
- Changing entry mode (wick vs crossover) based on pair characteristics

---

## Performance Metrics

### Trade-Level Metrics

```
Win Rate = (Number of winning trades) / (Total trades) * 100%

Average Win = avg(PnL[PnL > 0])
Average Loss = avg(PnL[PnL < 0])

Profit Factor = sum(winning PnL) / sum(|losing PnL|)

Avg Duration = mean(exit_time - entry_time)

ADF Quality = mean(ADF p-value at entries)
              (lower = more stationary spreads)
```

### Portfolio-Level Metrics

```
Total Return = (Final Equity - Initial Equity) / Initial Equity * 100%

Sharpe Ratio = mean(daily_returns) / std(daily_returns) * sqrt(252)
               (higher = better risk-adjusted returns)

Max Drawdown = (Peak Equity - Trough) / Peak * 100%
               (lower = smoother equity)

Calmar Ratio = Total Return / Max Drawdown
               (higher = better returns per unit of drawdown)

Win Rate = (Profitable days) / (Total days) * 100%

Correlation to Benchmark = corr(equity, benchmark)
```

### Signals for Strategy Quality

| Metric | Good | Bad |
|--------|------|-----|
| **ADF Quality** | < 0.05 | > 0.20 |
| **Win Rate** | > 55% | < 45% |
| **Max DD vs Return** | DD < 2x Return | DD > 5x Return |
| **Profit Factor** | > 1.5 | < 1.2 |
| **Avg Win / DD%** | Positive | Negative |

---

## Limitations & Considerations

### Mathematical Assumptions

1. **Linearity:** Assumes linear relationship between pair and benchmark
   - Some pairs may have non-linear, regime-dependent relationships
   - Mitigation: Test with different benchmarks

2. **Stationarity > Cointegration:** ADF tests individual spreads
   - Full cointegration testing (Johansen test) is more rigorous
   - ADF is simpler and works well in practice

3. **Normal Distribution:** Z-scores assume spreads are normally distributed
   - Reality: Financial data has fat tails (extreme events more frequent)
   - Mitigation: Use conservative thresholds (±3 instead of ±2)

4. **Constant Parameters:** Regression window fixed at 50 candles
   - Ideal implementation adapts window to current volatility
   - Could use VIX-adjusted windows

### Practical Limitations

1. **Correlation Breaks:** Pairs may decouple from benchmark permanently
   - Example: ECB policy divergence → EUR/USD rho with DXY changes
   - Monitor beta stability over time

2. **Illiquidity in Pairs:** Some currency pairs have wide spreads
   - Strategy assumes tight spreads (Dukascopy BID prices)
   - Live trading spreads will be wider

3. **Data Quality:** Dukascopy data occasionally has gaps
   - Strategy uses forward-fill (assumes no trades during gap)
   - Check data for continuous coverage

4. **Overnight Risk:** Backtester assumes 24/5 markets; real markets have gaps
   - Friday close → Monday open can have significant moves
   - Add buffer for overnight gaps in real trading

5. **Black Swan Events:** Strategy has no tail-risk hedge
   - March 2020, Brexit, CHF unpegging: extreme deviations break mean reversion
   - Consider reducing leverage or adding options hedges

### Market Regime Changes

Strategy works best when:
- ✅ Pairs maintain stable correlations with benchmark
- ✅ Spreads oscillate around mean (no trends)
- ✅ Volatility is moderate (no sudden spikes)

Strategy struggles when:
- ❌ Regime shifts occur (Fed policy changes, geopolitical events)
- ❌ New era begin (correlation permanently break)
- ❌ Volatility explodes (extreme outliers, no mean reversion)

**Mitigation:**
- Monitor beta coefficient drift over time
- Disable strategy during major news events
- Reduce position size during high-volatility periods
- Use stop-losses generously

### Walk-Forward Optimization

For production trading:

1. **Development Period** (Year 1): Backtest full year, optimize parameters
2. **Test Period** (Year 2): Forward-test optimized parameters
3. **Out-of-Sample Period** (Months 13-24): Trade without reoptimization
4. **Results:** Compare dev/test/OOS performance to detect overfitting

If OOS performance < 50% of test performance → model is overfit → restart.

---

## Advanced Topics

### Multi-Timeframe Analysis

Current implementation uses single timeframe. For robustness:

```
1. Generate signals on 1H timeframe (fast)
2. Confirm on 4H timeframe (slow)
3. Check direction on 1D timeframe (trend)

Entry only if: 1H signal AND 4H confirmation AND 1D not opposite
```

### Machine Learning Enhancement

Instead of fixed Z-score thresholds, train model:

```python
# Features
features = [
    z_score,           # current level
    z_score_velocity,  # d(z)/dt
    adf_pvalue,        # spread stationarity
    beta,              # correlation strength
    volatility         # recent spread volatility
]

# Target
target = [1 if trade_profitable else 0]  # binary classification

# Fit
model = RandomForest()
model.fit(features, target)

# Generate signals
prediction = model.predict(features[-1])
```

### Ensemble Strategy

Combine multiple benchmarks:

```
signal_score = [
    0.5 * signal_vs_DXY +
    0.3 * signal_vs_Gold +
    0.2 * signal_vs_Oil
]

Enter if signal_score > threshold
```

---

## Conclusion

The Forex PCA Statistical Arbitrage strategy:

1. **Identifies** mean-reverting deviations between pairs and benchmarks
2. **Validates** using ADF stationarity testing
3. **Trades** Z-score extremes with proper risk management
4. **Backtests** without look-ahead bias
5. **Produces** consistent signals across market conditions

Strengths: Simple, mathematically sound, adaptable benchmarks  
Weaknesses: Regime-dependent, correlation-fragile, overnight gaps  

Best used as **one component of a diversified trading system**, not as standalone strategy in live trading without additional risk controls and out-of-sample validation.

---

**Written:** February 2026  
**Author:** StratFRIZE Team  
**Version:** 1.0.0
