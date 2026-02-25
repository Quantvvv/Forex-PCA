# Forex PCA Statistical Arbitrage Backtester

A quantitative analysis tool that identifies statistical arbitrage opportunities in forex pairs using Principal Component Analysis (PCA) principles and mean-reversion strategies. The system analyzes currency pair deviations from benchmark instruments (USD Index, Gold, Oil) and validates trading signals using econometric tests.

![Python](https://img.shields.io/badge/Python-3.8+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.28+-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![Pandas](https://img.shields.io/badge/Pandas-2.0+-150458?style=for-the-badge&logo=pandas&logoColor=white)
![NumPy](https://img.shields.io/badge/NumPy-1.24+-013243?style=for-the-badge&logo=numpy&logoColor=white)
![Statsmodels](https://img.shields.io/badge/Statsmodels-0.13+-blue?style=for-the-badge)
![Plotly](https://img.shields.io/badge/Plotly-5.10+-3F4F75?style=for-the-badge&logo=plotly&logoColor=white)
![Dukascopy](https://img.shields.io/badge/Dukascopy-API-orange?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

---

## 🎯 Project Objectives

The primary goal is to move beyond simple technical analysis and examine the underlying structure of forex correlations:

- **Correlation Decomposition**: Separate benchmark effects from pair-specific deviations (mean-reversion opportunities)
- **Spread Stationarity**: Use the Augmented Dickey-Fuller (ADF) test to validate that deviations revert to equilibrium
- **Risk-Adjusted Entry Signals**: Combine Z-score mean-reversion with statistical significance testing
- **Portfolio Risk Management**: Control position sizing, drawdown, and concurrent exposure across 30+ pairs
- **Interactive Backtesting**: Test strategies across multiple timeframes (30m to 1w) with high-frequency Dukascopy data

---

## 🛠 Project Workflow

### 1. Data Universe Selection
- Automatically downloads OHLC data (30m to 1w) from Dukascopy for major/minor forex pairs
- Supports custom pair whitelists for focused analysis
- Downloads benchmark data (DXY, Gold, Silver, Brent, WTI) for correlation analysis

### 2. Correlation & Regression Analysis
- Fits a linear regression model: `pair_price = α + β*benchmark_price + ε (residual)`
- Extracts the residual component (spread) representing pair-specific deviation from benchmark
- Calculates rolling Z-scores of the spread to identify over/undervaluation

### 3. Stationarity Verification
- Applies the Augmented Dickey-Fuller (ADF) test on each pair's spread
- Only pairs with p-value < threshold (default 0.05) are deemed stationary (mean-reverting)
- Filters out non-stationary spreads that could produce false signals

### 4. Signal Generation & Entry Modes
- **Standard Mode**: Enters when Z-score crosses predefined thresholds (e.g., -2 for LONG, +2 for SHORT)
- **Wick Mode**: Enters when previous candle's HIGH/LOW touches trigger level (faster reaction)
- Validates all entries meet ADF stationarity requirement before execution

### 5. Portfolio Risk Management
- **Position Sizing**: Capital divided by concurrent position count (realistic account modeling)
- **Max Concurrent Positions**: Limits total portfolio exposure (default: 200 positions max)
- **Max Per Pair**: Prevents over-concentration on individual pairs (default: 5 per pair)
- **Stop-Loss & Cooldown**: Exit rules and whipsaw prevention across all positions

### 6. Backtesting & Analysis  
- Simulates historical execution with slippage and commissions
- Generates equity curves, trade logs, and pair-level statistics
- Compares raw signal quality vs. realistic capital allocation effects

---

## 📊 Key Visualizations

**Interactive Dashboard** (Streamlit):
- **Real-time Signals Table** - Current Z-score, ADF p-value, and buy/sell flags for all pairs
- **Equity Curve** - Portfolio performance with drawdown zones and trade entry/exit annotations  
- **Pair-Level Analysis**:
  - Price chart with entry/exit markers (🟢 Long | 🔴 Short | 🟨 Exit)
  - Z-Score evolution with overbought/oversold zones
  - Correlation heatmap of analyzed pairs
- **Performance Metrics** - Win rate, total trades, average holding period, max drawdown

---

## 🚀 Installation & Usage

**Dependencies:**
```bash
pip install -r requirements.txt
```

**Execution:**
```bash  
streamlit run forex_pca_backtester.py
```

The app opens at `http://localhost:8501`. Configure your backtest:
1. Select benchmark (DXY, Gold, Silver, Brent, WTI)
2. Choose pair universe (Major Pairs, Major+Minor, or custom)
3. Set timeframe (30m, 1h, 4h, 1d, 1w)
4. Adjust Z-score entry thresholds and ADF p-value filter
5. Click **START BACKTEST** to download and analyze

⚠️ For detailed strategy parameters, risk settings, and example configurations, see the **TECHNICAL_MANUAL.md**.

---

## 💡 Why This Matters for Finance

In a quantitative finance context, this approach demonstrates:

- **Econometric Rigor**: ADF stationarity tests replace subjective signals with statistical validation
- **Systemic Risk Control**: Examining correlations reveals how pairs move together under market stress
- **Mean Reversion as Edge**: Historical correlation patterns create exploitable deviations (statistical arbitrage)
- **Portfolio Optimization**: Multi-pair framework with realistic capital allocation models realistic account constraints
- **Reproducibility**: Fully parametrized system allows hypothesis testing and walk-forward validation

---

## 📚 Documentation

- **Strategy Details** - See [TECHNICAL_MANUAL.md](TECHNICAL_MANUAL.md) for mathematical foundations, signal mechanics, and configuration examples
- **Troubleshooting** - See [TECHNICAL_MANUAL.md](TECHNICAL_MANUAL.md#troubleshooting) for common issues

---

## ⚠️ Disclaimer

**This is a backtesting tool, not investment advice.**

- Past performance ≠ future results
- Backtests can be over-optimized and fail in live trading
- Forex trading carries substantial risk of total loss
- Always test strategies with small capital first
- Consult a financial advisor before trading with real money

Use at your own risk. The authors assume no liability for trading losses.
