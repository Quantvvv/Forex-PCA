# Forex PCA Backtester

A statistical arbitrage backtester for forex pairs using principal component analysis (PCA) principles and mean-reversion strategies. Analyzes currency pair correlations with a benchmark instrument (US Dollar Index, Gold, Oil, etc.) to identify trading opportunities.

**Data Source:** Dukascopy | **UI Framework:** Streamlit | **License:** MIT

---

## Features

✅ **Statistical Arbitrage** - Identifies mean-reverting spread patterns in forex pairs  
✅ **Multiple Entry Modes** - Standard Z-score crossover OR wick entry (previous candle touch)  
✅ **Cointegration Testing** - ADF test validates stationarity before entering trades  
✅ **Portfolio Risk Management** - Position sizing, stop-loss, max concurrent positions, cooldown  
✅ **Flexible Benchmarks** - Compare pairs against DXY, Gold, Silver, Brent Oil, or WTI  
✅ **Interactive Dashboard** - Real-time equity curves, trade annotations, detailed pair analysis  
✅ **Historical Backtesting** - Download up to 5000+ days of OHLC data from Dukascopy  

---

## Installation

### Prerequisites
- Python 3.8 or higher
- pip package manager

### Step 1: Clone or Download

```bash
git clone <your-repo-url>
cd forex-pca-backtester
```

### Step 2: Create Virtual Environment (Recommended)

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Key packages:**
```bash
pip install streamlit>=1.28.0
pip install pandas>=2.0.0
pip install numpy>=1.24.0
pip install dukascopy-python>=0.0.5
pip install statsmodels>=0.13.0
pip install plotly>=5.10.0
```

---

## Quick Start

### Run the Backtester

```bash
streamlit run forex_pca_backtester.py
```

The app will open at `http://localhost:8501` in your default browser.

### First Backtest Steps

1. **Select Benchmark:** Choose what to compare pairs against (default: DXY)
2. **Select Pairs:** Use Major Pairs, Major+Minor, or create a custom whitelist
3. **Set Timeframe:** Choose 30m, 1h, 4h, 1d, or 1w
4. **Configure Strategy:**
   - Set Z-score entry/exit thresholds (e.g., -3 for long entry, +3 for short entry)
   - Adjust regression window (50 by default)
   - Set ADF p-value threshold (0.05 for strict stationarity test)
5. **Risk Settings:**
   - Set max concurrent positions (default: 200)
   - Set stop-loss % (e.g., 0.5% = ~50 pips for EURUSD)
   - Enable/disable pyramiding (multiple positions per pair)
6. **Click "START BACKTEST"** and wait for download + analysis

---

## File Structure

```
forex-pca-backtester/
├── forex_pca_backtester.py        # Main Streamlit app (ENGLISH)
├── ForexPCAscan.py                # Original Russian version
├── README.md                       # This file
├── TECHNICAL_MANUAL.md             # Detailed strategy & math documentation
├── requirements.txt                # Python dependencies
└── CHANGELOG.md                    # Version history
```

---

## Configuration Guide

### 📊 Benchmark Selection
- **US Dollar Index (DXY)** - Tracks USD strength; pairs often anti-correlated
- **Gold (XAU/USD)** - Risk sentiment indicator; useful for commodity currencies
- **Silver (XAG/USD)** - Higher volatility than gold
- **Brent Oil** - Energy demand indicator
- **WTI (Light Crude)** - US energy benchmark

### 📈 Strategy Parameters

| Parameter | Default | Range | Meaning | Note |
|-----------|---------|-------|---------|------|
| **Regression Window** | 50 | 20-200 | Candles used to fit pair vs benchmark regression | - |
| **Long Entry Z** | -2.00 | -5 to +5 | Z-score threshold to enter LONG (undervalued) | **Proven stable** |
| **Long Exit Z** | 1.50 | -5 to +5 | Z-score threshold to exit LONG (reverted) | - |
| **Short Entry Z** | +2.00 | -5 to +5 | Z-score threshold to enter SHORT (overvalued) | **Proven stable** |
| **Short Exit Z** | -1.50 | -5 to +5 | Z-score threshold to exit SHORT (reverted) | - |
| **ADF p-value** | 0.05 | 0.01-1.00 | Max p-value to accept spread as stationary | - |
| **Lookback Days** | 365 | 30-5000 | Historical days to download (timeframe-dependent) | - |

### 🛡 Risk Management

| Parameter | Default | Meaning |
|-----------|---------|---------|
| **Max Concurrent** | 200 | Maximum open positions across all pairs |
| **Max Per Pair** | 5 | Maximum concurrent positions on single pair (proven stable) |
| **Stop Loss %** | 0.5% | Exit if position loses X% (e.g., 0.5% ≈ 50 pips EURUSD) |
| **Cooldown (candles)** | 1 | Wait N candles between entries on same pair (prevents whipsaw) |
| **Commission %** | 0.01% | Bid-ask spread + broker fees per trade |
| **Capital Allocation** | **Always On** | Each position's PnL divided by concurrent count (realistic) |

### ⚡ Entry Modes

**Standard Mode (Default):**
- Enters when Z-score crosses thresholds between consecutive candles
- Clean, no look-ahead bias
- Example: Z-score goes from -3.5 to -2.9 → enter LONG

**Wick Entry Mode:**
- Enters when previous candle's HIGH/LOW touches the trigger level
- Entry executes on current candle's close
- Catches mean-reversion faster but requires more analysis
- **No look-ahead bias** - uses only previous candle's wicks

---

## Understanding the Output

### Market Status Table
Displays current trading signals for all analyzed pairs:
- **🟢 BUY SIGNAL** - Undervalued + stationary spread + Z-crossed threshold
- **🔴 SELL SIGNAL** - Overvalued + stationary spread + Z-crossed threshold
- **⏳ Undervalued/Overvalued** - Signal triggered but ADF p-value too high
- **-** - No signal

### Key Metrics
- **Total PnL (equity)** - Portfolio profit/loss as % of capital (position-weighted)
- **Total Trades** - Number of closed positions
- **Win Rate** - % of profitable trades
- **Max Positions** - Peak concurrent open positions
- **Max Drawdown** - Largest drop from equity peak to trough

⚠️ **Important:** Max Drawdown can exceed 100% in backtests. This represents losses on a theoretical "infinite capital" account. Here's why:

The backtester uses **capital division by concurrent positions** (realistic mode). When many positions lose simultaneously:
- 10 open positions, $1K each = $10K equity needed
- All 10 lose 5% each = -$500 total
- Peak equity was $20K, now at $19.5K = -2.5% drawdown ✅

But if positions have different timing and some lose while others are newly opened:
- Peak equity: $50K (many positions open)
- Trough equity: -$10K (extreme simultaneous losses)
- Drawdown: (-$10K - $50K) / $50K = -120% 

**In real trading:** Hit 100% drawdown = account blown. But in backtests, this metric shows the raw magnitude of underwater periods if capital were unlimited. Use **Max Concurrent** and **Max Per Pair** limits to prevent realistic account blowouts.

### Pair Summary Table
- **PnL %** - Total profit/loss for that pair
- **Trades** - Number of closed trades
- **Win Rate %** - Percentage of winning trades
- **Avg Time** - Average holding duration
- **Avg ADF** - Average ADF p-value of entries (lower = more stationary)
- **Current Z** - Latest Z-score value

### Detailed Charts
- **Price chart** - Raw pair price with entry/exit markers
  - 🟢 Triangle up = Long entry
  - 🔴 Triangle down = Short entry
  - 🟨 X = Exit (profit or stop-loss)
- **Z-Score chart** - Mean-reversion indicator with entry zones marked

---

## Performance Tips

### Optimize Entry Parameters
- **More trades:** Lower entry thresholds (e.g., -2 instead of -3)
- **Higher quality entries:** Raise thresholds or ADF p-value threshold
- **Balance:** Default (-3/+3) usually good starting point

### Optimize Risk Parameters
- **Fewer concurrent:** Lower max_concurrent to reduce capital at risk
- **Tighter stops:** Reduce stop-loss % for faster exits
- **More filters:** Increase ADF p-value requirement (0.01 is strict)

### Optimize Regression Window
- **Short window (20-30):** Faster adaptation, more false signals
- **Long window (50-100):** Slower to adapt, fewer false signals
- **50 is recommended** for 1h+ timeframes

### Capital Allocation Modes

**Mode: "Divide capital by positions" (Always Enabled - Realistic)**
- If 10 positions open on $10K account = $1K per position
- Each position's PnL is weighted by concurrent count
- More accurate for real account sizing validation
- **This is the only mode used in backtests** - capital is always divided by position count

The "raw sum" metric shown (bottom of results) represents what would happen if each position was on full capital, useful for assessing pure signal quality independent of position sizing.

---

## API & Data Limits

### Dukascopy API Constraints
- **30m candles:** Max ~60 days
- **1h candles:** Max ~729 days (~2 years)
- **4h candles:** Max ~730 days (~2 years)
- **1d candles:** Max 5000+ days (~13 years)
- **1w candles:** Max 5000+ days (~96 years)

**Note:** These are approximate; actual limits depend on Dukascopy server.

### Download Speed
- Typical: 20-50 pairs × 365 days = 1-3 minutes
- Slow connection: 5-10 minutes
- Retries automatically on failure

---

## Troubleshooting

### "Failed to download any instruments"
- Check internet connection
- Verify pair names (e.g., EURUSD not EUR/USD)
- Try longer timeframe (lower frequency = more stable download)

### "No data available for analysis"
- Ensure at least 1 pair was downloaded successfully
- Check benchmark (DXY, Gold, etc.) is available
- Try reducing lookback_days

### ADF p-value always > 0.05
- Spread is not stationary on current parameters
- Try: longer regression window, different benchmark, or higher ADF threshold
- This is normal for some pairs/timeframes

### No trades generated
- Z-score thresholds too extreme (e.g., -10 is unrealistic)
- Regression window too short
- Benchmark and pair not correlated
- Try: lower entry thresholds (-2.5 instead of -3)

### Slow performance
- Download fewer days or pairs
- Use longer timeframes (1h, 4h instead of 30m)
- Increase cooldown to reduce trade count

---

## Example Configurations

### Conservative (High Quality Signals)
```
Timeframe:         1h
Regression:        100
Entry Z:           Long -2.5, Short +2.5
Exit Z:            Long +1.5, Short -1.5
ADF p-value:       0.01 (strict)
Stop Loss:         1.0%
Max Concurrent:    30
Max Per Pair:      3
Cooldown:          2
Commission:        0.02%
```

### Aggressive (High Trade Count)
```
Timeframe:         30m
Regression:        30
Entry Z:           Long -1.5, Short +1.5
Exit Z:            Long +0.8, Short -0.8
ADF p-value:       0.10 (loose)
Stop Loss:         0.3%
Max Concurrent:    200
Max Per Pair:      20
Cooldown:          0
Commission:        0.01%
```

### Balanced (Recommended & Proven Stable)
```
Timeframe:         1h or 4h
Regression:        50
Entry Z:           Long -2.0, Short +2.0
Exit Z:            Long +1.5, Short -1.5
ADF p-value:       0.05
Stop Loss:         0.5%
Max Concurrent:    100
Max Per Pair:      5
Cooldown:          1
Commission:        0.01%
Capital Allocation: On (always)
```
**← These are the default parameters - proven stable across different market conditions**

---

## Understanding Mean Reversion

The core strategy assumes:
1. **Pairs are cointegrated** with the benchmark (move together long-term)
2. **Short-term deviations exist** from the expected relationship
3. **These deviations revert to mean** (statistical arbitrage opportunity)

Example: EURUSD normally moves +1% when DXY moves -2.5%. If today EURUSD only +0.5% vs DXY -2.5%, EURUSD is undervalued → BUY signal (expect reversion).

---

## Contributing

Improvements welcome! Areas for enhancement:
- Machine learning entry optimization
- Multi-timeframe analysis
- Event-based filters (NFP, ECB, etc.)
- Live trading integration
- Additional benchmarks

---

## Disclaimer

**This is a backtesting tool, not investment advice.**

⚠️ Past performance ≠ future results  
⚠️ Backtests can be over-optimized and fail in live trading  
⚠️ Forex trading carries risk of total loss  
⚠️ Always test strategies with small capital first  
⚠️ Consult a financial advisor before trading  

Use at your own risk. The authors assume no liability for trading losses.

---

## Support & Documentation

- **Technical Details:** See `TECHNICAL_MANUAL.md`
- **Questions:** Review troubleshooting section above
- **Dukascopy Data:** https://www.dukascopy.com
- **Streamlit Docs:** https://docs.streamlit.io
- **Statsmodels ADF:** https://www.statsmodels.org/stable/generated/statsmodels.tsa.stattools.adfuller.html

---

## License

MIT License - Free to use, modify, and distribute. See LICENSE file for details.

---

**Last Updated:** February 2026  
**Version:** 1.0.0 (English Release)
