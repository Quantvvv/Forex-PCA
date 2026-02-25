"""
Forex PCA Backtester - Statistical Arbitrage Strategy
Analyzes forex pairs correlation with a benchmark (DXY, Gold, Oil, etc.)
Uses PCA-like approach to identify mean-reversion trading signals

Data Source: Dukascopy
Author: StratFRIZE
License: MIT
"""

import streamlit as st
import pandas as pd
import numpy as np
import dukascopy_python
from dukascopy_python.instruments import (
    INSTRUMENT_FX_MAJORS_EUR_USD,
    INSTRUMENT_FX_MAJORS_GBP_USD,
    INSTRUMENT_FX_MAJORS_USD_CHF,
    INSTRUMENT_FX_MAJORS_USD_JPY,
    INSTRUMENT_FX_MAJORS_AUD_USD,
    INSTRUMENT_FX_MAJORS_NZD_USD,
    INSTRUMENT_FX_MAJORS_USD_CAD,
    INSTRUMENT_FX_CROSSES_EUR_GBP,
    INSTRUMENT_FX_CROSSES_EUR_JPY,
    INSTRUMENT_FX_CROSSES_GBP_JPY,
    INSTRUMENT_FX_CROSSES_AUD_JPY,
    INSTRUMENT_FX_CROSSES_EUR_AUD,
    INSTRUMENT_FX_CROSSES_EUR_CHF,
    INSTRUMENT_FX_CROSSES_GBP_AUD,
    INSTRUMENT_FX_CROSSES_GBP_CHF,
    INSTRUMENT_FX_CROSSES_AUD_CAD,
    INSTRUMENT_FX_CROSSES_AUD_CHF,
    INSTRUMENT_FX_CROSSES_AUD_NZD,
    INSTRUMENT_FX_CROSSES_CAD_CHF,
    INSTRUMENT_FX_CROSSES_CAD_JPY,
    INSTRUMENT_FX_CROSSES_CHF_JPY,
    INSTRUMENT_FX_CROSSES_EUR_CAD,
    INSTRUMENT_FX_CROSSES_EUR_NZD,
    INSTRUMENT_FX_CROSSES_GBP_CAD,
    INSTRUMENT_FX_CROSSES_GBP_NZD,
    INSTRUMENT_FX_CROSSES_NZD_CAD,
    INSTRUMENT_FX_CROSSES_NZD_CHF,
    INSTRUMENT_FX_CROSSES_NZD_JPY,
    # Metals and Commodities
    INSTRUMENT_FX_METALS_XAU_USD,  # Gold
    INSTRUMENT_FX_METALS_XAG_USD,  # Silver
    INSTRUMENT_CMD_ENERGY_E_BRENT,  # Brent Oil
    INSTRUMENT_CMD_ENERGY_E_LIGHT,  # WTI Light Sweet Crude
    # Indices
    INSTRUMENT_IDX_AMERICA_DOLLAR_IDX_USD,  # US Dollar Index (DXY)
)

from dukascopy_python import (
    INTERVAL_MIN_30,
    INTERVAL_HOUR_1,
    INTERVAL_HOUR_4,
    INTERVAL_DAY_1,
    INTERVAL_WEEK_1,
    OFFER_SIDE_BID,
)
from statsmodels.tsa.stattools import adfuller
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime, timedelta

# ==========================================
# CONFIGURATION & MAPPINGS
# ==========================================
st.set_page_config(layout="wide", page_title="Forex PCA Backtester (Dukascopy)")

# Session state initialization for caching backtest results
if 'results_data' not in st.session_state: st.session_state.results_data = None
if 'trades_data' not in st.session_state: st.session_state.trades_data = None
if 'metrics_data' not in st.session_state: st.session_state.metrics_data = None
if 'selected_pair' not in st.session_state: st.session_state.selected_pair = None
if 'portfolio_metrics' not in st.session_state: st.session_state.portfolio_metrics = None
if 'last_scan_table' not in st.session_state: st.session_state.last_scan_table = None
if 'pair_summary_table' not in st.session_state: st.session_state.pair_summary_table = None

# Mapping of currency pair strings to Dukascopy instrument objects
FOREX_PAIRS_MAP = {
    # Major Pairs
    "EURUSD": INSTRUMENT_FX_MAJORS_EUR_USD,
    "GBPUSD": INSTRUMENT_FX_MAJORS_GBP_USD,
    "AUDUSD": INSTRUMENT_FX_MAJORS_AUD_USD,
    "NZDUSD": INSTRUMENT_FX_MAJORS_NZD_USD,
    "USDCAD": INSTRUMENT_FX_MAJORS_USD_CAD,
    "USDCHF": INSTRUMENT_FX_MAJORS_USD_CHF,
    "USDJPY": INSTRUMENT_FX_MAJORS_USD_JPY,
    # Cross Pairs (available in Dukascopy)
    "EURGBP": INSTRUMENT_FX_CROSSES_EUR_GBP,
    "EURJPY": INSTRUMENT_FX_CROSSES_EUR_JPY,
    "GBPJPY": INSTRUMENT_FX_CROSSES_GBP_JPY,
    "AUDJPY": INSTRUMENT_FX_CROSSES_AUD_JPY,
    "EURAUD": INSTRUMENT_FX_CROSSES_EUR_AUD,
    "EURCHF": INSTRUMENT_FX_CROSSES_EUR_CHF,
    "GBPAUD": INSTRUMENT_FX_CROSSES_GBP_AUD,
    "GBPCHF": INSTRUMENT_FX_CROSSES_GBP_CHF,
    "AUDCAD": INSTRUMENT_FX_CROSSES_AUD_CAD,
    "AUDCHF": INSTRUMENT_FX_CROSSES_AUD_CHF,
    "AUDNZD": INSTRUMENT_FX_CROSSES_AUD_NZD,
    "CADCHF": INSTRUMENT_FX_CROSSES_CAD_CHF,
    "CADJPY": INSTRUMENT_FX_CROSSES_CAD_JPY,
    "CHFJPY": INSTRUMENT_FX_CROSSES_CHF_JPY,
    "EURCAD": INSTRUMENT_FX_CROSSES_EUR_CAD,
    "EURNZD": INSTRUMENT_FX_CROSSES_EUR_NZD,
    "GBPCAD": INSTRUMENT_FX_CROSSES_GBP_CAD,
    "GBPNZD": INSTRUMENT_FX_CROSSES_GBP_NZD,
    "NZDCAD": INSTRUMENT_FX_CROSSES_NZD_CAD,
    "NZDCHF": INSTRUMENT_FX_CROSSES_NZD_CHF,
    "NZDJPY": INSTRUMENT_FX_CROSSES_NZD_JPY,
}

# Benchmark instruments for correlation analysis
BENCHMARK_MAP = {
    "US Dollar Index (DXY)": ("DXY", INSTRUMENT_IDX_AMERICA_DOLLAR_IDX_USD, "indigo"),
    "Gold (XAU/USD)": ("XAU", INSTRUMENT_FX_METALS_XAU_USD, "gold"),
    "Silver (XAG/USD)": ("XAG", INSTRUMENT_FX_METALS_XAG_USD, "lightgray"),
    "Brent Oil": ("BRENT", INSTRUMENT_CMD_ENERGY_E_BRENT, "darkred"),
    "WTI (Light Crude)": ("WTI", INSTRUMENT_CMD_ENERGY_E_LIGHT, "red"),
}

# ==========================================
# SIDEBAR CONFIGURATION
# ==========================================
st.sidebar.header("🛠 Portfolio Settings")

# Benchmark selection
st.sidebar.markdown("### 📊 Benchmark Selection")
benchmark_name = st.sidebar.selectbox(
    "Compare currency pairs with:",
    list(BENCHMARK_MAP.keys()),
    index=0,
    help="Select the benchmark instrument for correlation analysis (default: DXY)"
)
selected_benchmark_display, selected_benchmark_instrument, benchmark_color = BENCHMARK_MAP[benchmark_name]

st.sidebar.markdown("---")

# Predefined currency pair lists
forex_major_pairs = [
    "EURUSD",  # Euro / US Dollar
    "GBPUSD",  # British Pound / US Dollar
    "AUDUSD",  # Australian Dollar / US Dollar
    "NZDUSD",  # New Zealand Dollar / US Dollar
    "USDCAD",  # US Dollar / Canadian Dollar
    "USDCHF",  # US Dollar / Swiss Franc
    "USDJPY",  # Japanese Yen / US Dollar
]

forex_minor_pairs = [
    "EURGBP",  # Euro / British Pound
    "EURJPY",  # Euro / Japanese Yen
    "GBPJPY",  # British Pound / Japanese Yen
    "AUDJPY",  # Australian Dollar / Japanese Yen
    "EURAUD",  # Euro / Australian Dollar
    "EURCHF",  # Euro / Swiss Franc
    "GBPAUD",  # British Pound / Australian Dollar
    "GBPCHF",  # British Pound / Swiss Franc
    "AUDCAD",  # Australian Dollar / Canadian Dollar
    "AUDCHF",  # Australian Dollar / Swiss Franc
    "AUDNZD",  # Australian Dollar / New Zealand Dollar
    "CADCHF",  # Canadian Dollar / Swiss Franc
    "CADJPY",  # Canadian Dollar / Japanese Yen
    "CHFJPY",  # Swiss Franc / Japanese Yen
    "EURCAD",  # Euro / Canadian Dollar
    "EURNZD",  # Euro / New Zealand Dollar
    "GBPCAD",  # British Pound / Canadian Dollar
    "GBPNZD",  # British Pound / New Zealand Dollar
    "NZDCAD",  # New Zealand Dollar / Canadian Dollar
    "NZDCHF",  # New Zealand Dollar / Swiss Franc
    "NZDJPY",  # New Zealand Dollar / Japanese Yen
]

st.sidebar.markdown("---")
st.sidebar.markdown("### 📈 Currency Pair Selection")

list_option = st.sidebar.radio("Select pairs:", ["Major Pairs Only", "Major + Minor", "Manual Whitelist"], index=1)

if list_option == "Major Pairs Only":
    pair_list = forex_major_pairs
    st.sidebar.info(f"Selected {len(pair_list)} major pairs")
elif list_option == "Major + Minor":
    pair_list = list(set(forex_major_pairs + forex_minor_pairs))
    st.sidebar.info(f"Selected {len(pair_list)} pairs (Major + Minor)")
else:
    default_list = "AUDUSD, NZDUSD, USDCAD, USDCHF, USDJPY, EURGBP, GBPJPY, AUDJPY, EURAUD, EURCHF, GBPAUD, GBPCHF, AUDCAD, AUDCHF, CADJPY, CHFJPY, EURCAD, EURNZD, GBPCAD, GBPNZD, NZDCAD, NZDCHF, NZDJPY"
    whitelist_raw = st.sidebar.text_area("Pair list (Dukascopy format, comma-separated):", value=default_list)
    pair_list = [c.strip().upper() for c in whitelist_raw.split(",") if c.strip()]

# Timeframe configuration
timeframe_list = ["30m", "1h", "4h", "1d", "1wk"]
selected_timeframe = st.sidebar.selectbox("Timeframe", timeframe_list, index=1, help="OHLC bar period")

# History depth limits per timeframe (Dukascopy API constraints)
max_days_map = {"30m": 60, "1h": 729, "4h": 730, "1d": 5000, "1wk": 5000}
max_days = max_days_map.get(selected_timeframe, 729)
lookback_days = st.sidebar.slider("History lookback (days)", 30, max_days, 365, 
                                   help="Number of historical candles to download")
regression_window = st.sidebar.slider("Regression window (candles)", 20, 200, 50,
                                      help="Rolling window for linear regression (spread calculation)")

st.sidebar.markdown("---")
st.sidebar.markdown("### 🛡 Risk Management")
max_concurrent_limit = st.sidebar.slider("Max concurrent positions", 1, 200, 200,
                                         help="Maximum simultaneous open positions across all pairs")
stop_loss_pct = st.sidebar.slider(
    "Stop Loss (%)", 
    0.0, 5.0, 0.5, 0.1,
    help="Stop loss as % price change (Forex: 0.5% ≈ 50 pips, 1% ≈ 100 pips, 2% ≈ 200 pips)"
)
allow_multiple = st.sidebar.checkbox("Allow position pyramiding", value=True,
                                     help="Whether to open multiple positions on same pair")
max_pos_per_pair = st.sidebar.slider("Max positions per pair", 1, 50, 5,
                                     help="Maximum concurrent positions on single pair (default 5: proven stable)") if allow_multiple else 1
cooldown_candles = st.sidebar.slider("Cooldown period (candles)", 0, 50, 1,
                                     help="Candles to wait before opening next position on same pair (default 1: prevents whipsaw)")

st.sidebar.markdown("---")
st.sidebar.markdown("### 💰 Fees & Capital")
commission_pct = st.sidebar.number_input("Commission (%)", min_value=0.0, max_value=5.0, value=0.01, step=0.005,
                                         help="Bid-ask spread + broker commission (Forex typically 0.001-0.05%)")
use_position_sizing = True  # Always enabled - capital divided by concurrent positions (realistic allocation)

st.sidebar.markdown("---")
st.sidebar.markdown(f"### 🚦 Strategy Settings (vs {selected_benchmark_display})")
use_wick_entry = st.sidebar.checkbox("⚡ Wick Entry", value=False,
                                     help="Enter when previous candle's wick touches trigger levels (based on candle k-1 High/Low)")

col1, col2 = st.sidebar.columns(2)
with col1:
    long_entry_z = st.number_input("Long entry Z < (Undervalued)", value=-2.00,
                                   help="Z-score threshold to enter long positions (default -2: proven stable)")
    long_exit_z = st.number_input("Long exit Z >", value=1.50,
                                  help="Z-score threshold to exit long positions")
with col2:
    short_entry_z = st.number_input("Short entry Z > (Overvalued)", value=2.00,
                                    help="Z-score threshold to enter short positions (default 2: proven stable)")
    short_exit_z = st.number_input("Short exit Z <", value=-1.50,
                                   help="Z-score threshold to exit short positions")

adf_max_threshold = st.sidebar.slider("ADF P-Value (Cointegration)", 0.01, 1.00, 0.05,
                                      help="Max p-value for ADF test (stationarity check). Lower = more stringent. Default: 0.05")

start_button = st.sidebar.button("🚀 START BACKTEST", type="primary", use_container_width=True)

# ==========================================
# UTILITY FUNCTIONS
# ==========================================

def format_duration(td):
    """Format timedelta to human-readable string (e.g., '5d 3h', '2h')"""
    if pd.isna(td) or td == pd.Timedelta(0): 
        return "-"
    total = int(td.total_seconds())
    days = total // 86400
    hours = (total % 86400) // 3600
    if days > 0:
        return f"{days}d {hours}h"
    else:
        return f"{hours}h"

def load_forex_data(days, timeframe_str, ticker_list, benchmark_instrument, benchmark_name):
    """
    Download forex OHLC data from Dukascopy via dukascopy-python library.
    
    Parameters:
    -----------
    days : int
        Number of historical days to download
    timeframe_str : str
        Timeframe identifier: "30m", "1h", "4h", "1d", "1wk"
    ticker_list : list
        Currency pair strings (e.g., ["EURUSD", "GBPUSD"])
    benchmark_instrument : object
        Dukascopy instrument object for benchmark
    benchmark_name : str
        Display name for benchmark (e.g., "DXY")
    
    Returns:
    --------
    tuple(DataFrame, DataFrame, DataFrame)
        (df_close, df_high, df_low) with synchronized timestamps
    """
    
    # Map timeframe strings to Dukascopy interval constants
    tf_map = {
        "30m": INTERVAL_MIN_30,
        "1h": INTERVAL_HOUR_1,
        "4h": INTERVAL_HOUR_4,
        "1d": INTERVAL_DAY_1,
        "1wk": INTERVAL_WEEK_1,
    }
    
    interval = tf_map.get(timeframe_str, INTERVAL_HOUR_1)
    offer_side = OFFER_SIDE_BID  # Use BID prices for realistic backtesting
    
    # Calculate date range (from 'days ago' to now)
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    progress = st.progress(0, text="Downloading Forex data from Dukascopy...")
    
    try:
        # Dictionary to store raw OHLC data for each pair
        data_dict = {}
        downloaded_pairs = []
        benchmark_loaded = False
        
        benchmark_instrument_obj = benchmark_instrument
        all_pairs_to_load = list(set(ticker_list + [benchmark_name]))
        
        for i, pair_name in enumerate(all_pairs_to_load):
            try:
                # Select instrument: benchmark or regular pair
                if pair_name == benchmark_name:
                    instrument = benchmark_instrument_obj
                else:
                    if pair_name not in FOREX_PAIRS_MAP:
                        st.warning(f"❌ Pair {pair_name} not found in Dukascopy base. Skipping.")
                        continue
                    instrument = FOREX_PAIRS_MAP[pair_name]
                
                # Download OHLC data via Dukascopy API
                df = dukascopy_python.fetch(
                    instrument=instrument,
                    interval=interval,
                    offer_side=offer_side,
                    start=start_date,
                    end=end_date,
                    max_retries=3
                )
                
                if df is not None and not df.empty:
                    df.index.name = 'timestamp'
                    if all(col in df.columns for col in ['open', 'high', 'low', 'close']):
                        data_dict[pair_name] = df
                        downloaded_pairs.append(pair_name)
                        if pair_name == benchmark_name:
                            benchmark_loaded = True
                        progress.progress((i + 1) / len(all_pairs_to_load), 
                                        text=f"Downloading: {i+1}/{len(all_pairs_to_load)} ({pair_name})")
                else:
                    st.warning(f"⚠️ No data for {pair_name}")
                    
            except Exception as e:
                st.warning(f"❌ Error downloading {pair_name}: {str(e)[:100]}")
                continue
        
        if not data_dict:
            st.error("Failed to download any instruments!")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        if not benchmark_loaded:
            st.error(f"❌ Failed to load benchmark {benchmark_name}. Try again later.")
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()
        
        st.success(f"✅ Benchmark loaded: {benchmark_name} | Total instruments: {len(downloaded_pairs)}")
        
        # Combine all close/high/low prices into separate DataFrames
        df_c = pd.DataFrame()
        df_h = pd.DataFrame()
        df_l = pd.DataFrame()
        
        for pair_name in downloaded_pairs:
            p_data = data_dict[pair_name]
            df_c[pair_name] = p_data['close']
            df_h[pair_name] = p_data['high']
            df_l[pair_name] = p_data['low']
        
        # Synchronize timestamps across all pairs (keep only common timestamps)
        common_index = df_c.index
        for pair_name in df_c.columns:
            common_index = common_index.intersection(df_c[pair_name].dropna().index)
            common_index = common_index.intersection(df_h[pair_name].dropna().index)
            common_index = common_index.intersection(df_l[pair_name].dropna().index)
        
        df_c = df_c.loc[common_index]
        df_h = df_h.loc[common_index]
        df_l = df_l.loc[common_index]
        
        # Remove rows where benchmark is missing
        df_c = df_c.dropna(subset=[benchmark_name])
        df_h = df_h.dropna(subset=[benchmark_name])
        df_l = df_l.dropna(subset=[benchmark_name])
        
        # Forward fill gaps in pair data (unrealistic but safer than dropping)
        df_c = df_c.ffill()
        df_h = df_h.ffill()
        df_l = df_l.ffill()
        
        # Remove incomplete last candle (it's not closed yet)
        df_c = df_c.iloc[:-1]
        df_h = df_h.iloc[:-1]
        df_l = df_l.iloc[:-1]

        progress.empty()

        # Standardize benchmark column name to 'DXY' for internal processing
        df_c = df_c.rename(columns={benchmark_name: 'DXY'})
        df_h = df_h.rename(columns={benchmark_name: 'DXY'})
        df_l = df_l.rename(columns={benchmark_name: 'DXY'})

        st.success(f"✅ Loaded {len(df_c)} candles for {len(df_c.columns) - 1} pairs + Benchmark ({benchmark_name})")

        return df_c, df_h, df_l
        
    except Exception as e:
        st.error(f"❌ Data download error: {str(e)}")
        progress.empty()
        return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

def calculate_backtest(df_c, df_h, df_l, reg_window, l_entry, l_exit, s_entry, s_exit, 
                       adf_thresh, max_per_pair, sl_pct, use_wick, cooldown, commission):
    """
    Execute statistical arbitrage backtest on forex pairs.
    
    Strategy:
    1. For each pair: calculate spread = log(pair_price) - linear_regression(pair vs benchmark)
    2. Z-score normalized spread identifies mean-reversion signals
    3. ADF test (Augmented Dickey-Fuller) confirms stationarity before entering
    4. Entry: when Z-score crosses thresholds (undervalued/overvalued)
    5. Exit: when Z-score reverts OR stop-loss hit
    
    Parameters:
    -----------
    df_c, df_h, df_l : DataFrame
        Synchronized OHLC data (close, high, low)
    reg_window : int
        Rolling window for regression (e.g., 50 candles)
    l_entry, l_exit, s_entry, s_exit : float
        Z-score thresholds for entry/exit
    adf_thresh : float
        ADF p-value threshold (max 0.05 for stationarity)
    max_per_pair : int
        Max simultaneous positions per pair
    sl_pct : float
        Stop loss in % price change
    use_wick : bool
        If True: enter on wick touch (previous candle); if False: Z-score crossover
    cooldown : int
        Candles to wait between entries on same pair
    commission : float
        Transaction costs in %
    
    Returns:
    --------
    dict : all_metrics, dict : all_trades, DataFrame : scan_results, DataFrame : pair_summary
    """
    pairs = [c for c in df_c.columns if c != 'DXY']
    all_metrics, all_trades, scan_results, pair_summary = {}, {}, [], {}
    
    # Global benchmark (DXY) in log space
    benchmark_log_full = np.log(df_c['DXY'])
    last_candle_time = df_c.index[-1].strftime('%Y-%m-%d %H:%M')
    
    for idx, pair in enumerate(pairs):
        # 1. Extract and align data
        temp_df = pd.concat([df_c[pair], df_h[pair], df_l[pair], benchmark_log_full], axis=1).dropna()
        if len(temp_df) < (reg_window + 105): 
            continue
        
        prices_c = temp_df.iloc[:, 0].values
        prices_h = temp_df.iloc[:, 1].values
        prices_l = temp_df.iloc[:, 2].values
        benchmark_log = temp_df.iloc[:, 3].values  # Benchmark in log scale
        pair_log = np.log(prices_c)
        times = temp_df.index
        n = len(temp_df)
        
        # 2. Rolling linear regression: fit pair_log = alpha + beta * benchmark_log
        #    Spread = residual = pair_log - (alpha + beta * benchmark_log)
        spreads = np.full(n, np.nan)
        r_betas = np.full(n, np.nan)
        r_alphas = np.full(n, np.nan)
        
        for j in range(reg_window, n):
            y_win = pair_log[j-reg_window:j]
            x_win = benchmark_log[j-reg_window:j]
            # polyfit returns [beta, alpha] for degree 1
            beta, alpha = np.polyfit(x_win, y_win, 1)
            spreads[j] = pair_log[j] - (beta * benchmark_log[j] + alpha)
            r_betas[j], r_alphas[j] = beta, alpha
        
        # 3. Z-score normalization of spread
        s_ser = pd.Series(spreads)
        r_mean = s_ser.rolling(50).mean().values
        r_std = s_ser.rolling(50).std().values
        z_vals = ((s_ser - r_mean) / r_std).values
        
        # 4. Simulation loop: generate trading signals
        trades, active_entries, direction, last_entry_idx = [], [], 0, -999
        
        for k in range(reg_window + 50, n):
            # Skip if z-score is undefined
            if np.isnan(z_vals[k]) or np.isnan(z_vals[k-1]): 
                continue
            
            curr_z, prev_z, curr_p = z_vals[k], z_vals[k-1], prices_c[k]
            
            # --- EXIT CHECK ---
            if direction != 0:
                triggered = False
                for entry in active_entries:
                    # Calculate unrealized PnL
                    if direction == 1:  # Long position
                        pnl = (curr_p - entry['price']) / entry['price'] * 100
                    else:  # Short position
                        pnl = (entry['price'] - curr_p) / entry['price'] * 100
                    
                    pnl_after_comm = pnl - commission
                    
                    # Check exit conditions: stop-loss OR Z-score reversal
                    stop_loss_hit = (sl_pct > 0 and pnl_after_comm < -sl_pct)
                    z_score_exit = (direction == 1 and curr_z > l_exit) or (direction == -1 and curr_z < s_exit)
                    
                    if stop_loss_hit or z_score_exit:
                        triggered = True
                        break
                
                # Close all positions if exit condition met
                if triggered:
                    for entry in active_entries:
                        if direction == 1:
                            pnl = (curr_p - entry['price']) / entry['price'] * 100
                        else:
                            pnl = (entry['price'] - curr_p) / entry['price'] * 100
                        
                        pnl_after_comm = pnl - (commission * 2)  # Entry + exit commissions
                        trades.append({
                            'Type': 'LONG' if direction == 1 else 'SHORT', 
                            'Entry Time': entry['time'], 
                            'Exit Time': times[k], 
                            'Entry Price': entry['price'], 
                            'Exit Price': curr_p, 
                            'PnL %': pnl_after_comm, 
                            'Duration': times[k] - entry['time'], 
                            'Entry ADF': entry['adf']
                        })
                    active_entries, direction = [], 0
            
            # --- ENTRY CHECK ---
            if (k - last_entry_idx) >= cooldown and len(active_entries) < max_per_pair:
                t_l, t_s, e_p = False, False, 0.0
                
                if use_wick:
                    # WICK ENTRY MODE: check if previous candle (k-1) touched trigger levels
                    # Entry executes on current candle (k) close price
                    p_s = np.exp((s_entry * r_std[k-1] + r_mean[k-1]) + r_betas[k-1] * benchmark_log[k-1] + r_alphas[k-1])
                    p_l = np.exp((l_entry * r_std[k-1] + r_mean[k-1]) + r_betas[k-1] * benchmark_log[k-1] + r_alphas[k-1])
                    
                    # Check if previous candle's high/low touched the trigger levels
                    if prices_h[k-1] >= p_s: 
                        t_s, e_p = True, curr_p
                    elif prices_l[k-1] <= p_l: 
                        t_l, e_p = True, curr_p
                else:
                    # STANDARD MODE: Z-score crossover (most common)
                    if prev_z < l_entry and curr_z >= l_entry: 
                        t_l, e_p = True, curr_p
                    elif prev_z > s_entry and curr_z <= s_entry: 
                        t_s, e_p = True, curr_p
                
                # Validate entry signal and check stationarity before entering
                if (t_l and direction != -1) or (t_s and direction != 1):
                    if t_l or t_s:
                        try:
                            # ADF test ensures the spread is mean-reverting (stationary)
                            p_val = adfuller(spreads[k-reg_window:k], autolag='AIC', regression='c')[1]
                            if p_val <= adf_thresh:
                                direction = 1 if t_l else -1
                                active_entries.append({'price': e_p, 'time': times[k], 'adf': p_val})
                                last_entry_idx = k
                        except: 
                            pass
        
        # 5. Collect results
        t_df = pd.DataFrame(trades)
        all_trades[pair] = t_df
        all_metrics[pair] = pd.DataFrame({'price': prices_c, 'z_score': z_vals}, index=times)
        
        if not t_df.empty:
            wins = len(t_df[t_df['PnL %'] > 0])
            win_rate = wins / len(t_df) * 100
            avg_duration = t_df['Duration'].mean()
        else:
            win_rate = 0
            avg_duration = pd.Timedelta(0)
        
        pair_summary[pair] = {
            'Pair': pair,
            'PnL %': t_df['PnL %'].sum() if not t_df.empty else 0,
            'Trades': len(t_df),
            'Win Rate %': win_rate,
            'Avg Time': avg_duration,
            'Avg ADF': t_df['Entry ADF'].mean() if not t_df.empty else 0,
            'Current Z': z_vals[-1] if not np.isnan(z_vals[-1]) else 0
        }
        
        # Calculate latest ADF p-value for signal evaluation
        try: 
            last_p_val = adfuller(spreads[-reg_window:], autolag='AIC', regression='c')[1]
        except: 
            last_p_val = 1.0
        
        # Determine current market signal status
        status = "-"
        if z_vals[-2] < l_entry and z_vals[-1] >= l_entry: 
            status = "🟢 BUY SIGNAL" if last_p_val <= adf_thresh else "⚠️ LONG (BAD ADF)"
        elif z_vals[-1] < l_entry: 
            status = "⏳ Undervalued"
        elif z_vals[-2] > s_entry and z_vals[-1] <= s_entry: 
            status = "🔴 SELL SIGNAL" if last_p_val <= adf_thresh else "⚠️ SHORT (BAD ADF)"
        elif z_vals[-1] > s_entry: 
            status = "⏳ Overvalued"
        
        scan_results.append({
            'Time': last_candle_time, 
            'Pair': pair, 
            'Price': prices_c[-1], 
            'Z-Score': z_vals[-1] if not np.isnan(z_vals[-1]) else 0, 
            'P-Value': last_p_val, 
            'Status': status
        })
    
    return all_metrics, all_trades, pd.DataFrame(scan_results), pd.DataFrame(pair_summary).T

def analyze_portfolio(all_trades, data_index, total_limit, use_position_sizing):
    """
    Aggregate trades across all pairs and calculate portfolio metrics.
    
    Parameters:
    -----------
    all_trades : dict
        Trades by pair {pair_name: DataFrame}
    data_index : Index
        Datetime index of market data (for alignment)
    total_limit : int
        Max concurrent positions across all pairs
    use_position_sizing : bool
        If True: divide PnL by concurrent count (realistic); 
        if False: sum all PnL without division
    
    Returns:
    --------
    dict : portfolio metrics (equity curve, exposure, drawdown, etc.)
    """
    # Combine all trades and sort by entry time
    combined = [df.assign(Coin=c) for c, df in all_trades.items() if not df.empty]
    if not combined: 
        return None
    
    df = pd.concat(combined).sort_values('Entry Time')
    final_trades, active_now = [], []
    
    # Filter trades respecting max concurrent limit
    for _, t in df.iterrows():
        # Remove trades that already exited before current entry
        active_now = [x for x in active_now if x['Exit Time'] > t['Entry Time']]
        
        # Add trade if under limit
        if len(active_now) < total_limit:
            final_trades.append(t)
            active_now.append(t)
    
    final_df = pd.DataFrame(final_trades)
    
    if final_df.empty:
        return None
    
    # Count concurrent positions at each trade entry
    entry_times = final_df['Entry Time'].values
    exit_times = final_df['Exit Time'].values
    concurrent_counts = np.array([
        np.sum((entry_times <= entry_times[i]) & (exit_times >= entry_times[i]))
        for i in range(len(final_df))
    ], dtype=float)
    concurrent_counts = np.maximum(concurrent_counts, 1)
    
    final_df = final_df.copy()
    final_df['Concurrent'] = concurrent_counts.astype(int)

    if use_position_sizing:
        # Realistic mode: capital divided among positions
        # Each position's PnL is divided by concurrent count
        final_df['PnL Weighted'] = final_df['PnL %'] / concurrent_counts
    else:
        # Signal aggregation mode: sum PnL without division
        final_df['PnL Weighted'] = final_df['PnL %']

    # Build equity curve from cumulative weighted PnL
    equity = final_df.groupby('Exit Time')['PnL Weighted'].sum().reindex(data_index, method='ffill').fillna(0).cumsum()

    # Calculate key metrics
    total_pnl = equity.iloc[-1]
    max_drawdown = (equity - equity.cummax()).min()
    raw_sum = final_df['PnL %'].sum()
    
    # Build exposure curve (number of open positions)
    exposure = pd.concat([
        pd.Series(1, index=final_df['Entry Time']), 
        pd.Series(-1, index=final_df['Exit Time'])
    ]).groupby(level=0).sum().cumsum().reindex(data_index, method='ffill').fillna(0)
    
    return {
        'trades': final_df,
        'equity': equity,
        'exposure': exposure,
        'max_drawdown': max_drawdown,
        'total_pnl': total_pnl,
        'raw_sum_pnl': raw_sum,
    }

# ==========================================
# MAIN EXECUTION & UI
# ==========================================

if start_button:
    df_c, df_h, df_l = load_forex_data(
        lookback_days, 
        selected_timeframe, 
        pair_list,
        selected_benchmark_instrument,
        selected_benchmark_display
    )
    
    if not df_c.empty:
        metrics, trades, scan_df, summary_df = calculate_backtest(
            df_c, df_h, df_l, 
            regression_window, 
            long_entry_z, long_exit_z, 
            short_entry_z, short_exit_z, 
            adf_max_threshold, 
            max_pos_per_pair, 
            stop_loss_pct, 
            use_wick_entry, 
            cooldown_candles, 
            commission_pct
        )
        
        st.session_state.results_data = analyze_portfolio(trades, df_c.index, max_concurrent_limit, use_position_sizing)
        st.session_state.metrics_data, st.session_state.trades_data, st.session_state.last_scan_table = metrics, trades, scan_df
        st.session_state.pair_summary_table = summary_df
        st.success("Backtest completed!")
    else:
        st.error("No data available. Check pair tickers and internet connection.")

# Display results if backtest was run
if st.session_state.results_data:
    p, scan = st.session_state.results_data, st.session_state.last_scan_table
    summ = st.session_state.pair_summary_table
    
    st.title(f"💱 Forex Pair Analysis vs {selected_benchmark_display} ({selected_timeframe}) [Dukascopy]")
    
    with st.expander("🔍 Current Market Status (Last Candle)", expanded=True):
        def color_status(val):
            if "BUY" in val: 
                color = '#00FF00'
            elif "SELL" in val: 
                color = '#FF0000'
            else: 
                color = 'white'
            return f'color: {color}'
        
        st.dataframe(
            scan.style.applymap(color_status, subset=['Status'])
            .format({'Z-Score': '{:.2f}', 'P-Value': '{:.4f}', 'Price': '{:.5f}'})
            .applymap(lambda x: 'color: red' if x > adf_max_threshold else 'color: green', subset=['P-Value']), 
            height=400, 
            use_container_width=True
        )
    
    st.markdown("---")
    
    st.caption(f"📊 **Capital Allocation Mode:** Each position's PnL divided by concurrent count (realistic)  |  Raw sum: `{p['raw_sum_pnl']:.2f}%`")
    
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("Total PnL (equity)", f"{p['total_pnl']:.2f}%")
    c2.metric("Total Trades", len(p['trades']))
    c3.metric("Win Rate", f"{(len(p['trades'][p['trades']['PnL %'] > 0])/len(p['trades'])*100):.1f}%")
    c4.metric("Max Positions", f"{int(p['exposure'].max())}")
    c5.metric("Max Drawdown", f"{p['max_drawdown']:.2f}%")
    
    equity_title = "Equity Curve — % of Capital (Position-Weighted)"
    fig = make_subplots(
        rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.08, 
        subplot_titles=(equity_title, "Exposure (Number of positions)"), 
        row_heights=[0.7, 0.3]
    )
    fig.add_trace(go.Scatter(x=p['equity'].index, y=p['equity'], line=dict(color="#00FF00", width=2), fill='tozeroy'), row=1, col=1)
    fig.add_trace(go.Scatter(x=p['exposure'].index, y=p['exposure'], line=dict(color="cyan", width=1), fill='tozeroy'), row=2, col=1)
    fig.update_layout(height=500, template="plotly_dark", showlegend=False)
    st.plotly_chart(fig, use_container_width=True)
    
    st.subheader("📈 Results by Currency Pair")
    summ_display = summ.copy()
    summ_display['Avg Time'] = summ_display['Avg Time'].apply(format_duration)
    st.dataframe(
        summ_display.sort_values('PnL %', ascending=False).style
        .format({'PnL %': '{:.2f}%', 'Win Rate %': '{:.1f}%', 'Avg ADF': '{:.4f}', 'Current Z': '{:.2f}'})
        .background_gradient(cmap='RdYlGn', subset=['PnL %']), 
        height=500, 
        use_container_width=True
    )
    
    st.markdown("---")
    
    available_pairs = summ.sort_values('PnL %', ascending=False)['Pair'].tolist()
    if available_pairs:
        sel_pair = st.selectbox("Detailed chart:", available_pairs)
        m, t = st.session_state.metrics_data[sel_pair], st.session_state.trades_data[sel_pair]
        
        fig2 = make_subplots(
            rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, 
            subplot_titles=(f"Price {sel_pair}", "Z-Score (Spread vs Benchmark)"), 
            row_heights=[0.6, 0.4]
        )
        fig2.add_trace(go.Scatter(x=m.index, y=m['price'], name="Price", line=dict(color='#636EFA')), row=1, col=1)
        
        if not t.empty:
            l, s = t[t['Type']=='LONG'], t[t['Type']=='SHORT']
            fig2.add_trace(go.Scatter(x=l['Entry Time'], y=l['Entry Price'], mode='markers', 
                                     marker=dict(color='lime', symbol='triangle-up', size=10), name="Long Entry"), row=1, col=1)
            fig2.add_trace(go.Scatter(x=s['Entry Time'], y=s['Entry Price'], mode='markers', 
                                     marker=dict(color='red', symbol='triangle-down', size=10), name="Short Entry"), row=1, col=1)
            fig2.add_trace(go.Scatter(x=t['Exit Time'], y=t['Exit Price'], mode='markers', 
                                     marker=dict(color='yellow', symbol='x', size=8), name="Exit"), row=1, col=1)
        
        fig2.add_trace(go.Scatter(x=m.index, y=m['z_score'], name="Z-Score", line=dict(color="orange")), row=2, col=1)
        fig2.add_hline(y=short_entry_z, line_color="red", line_dash="dash", annotation_text="Short Zone", row=2, col=1)
        fig2.add_hline(y=long_entry_z, line_color="lime", line_dash="dash", annotation_text="Long Zone", row=2, col=1)
        fig2.add_hline(y=0, line_color="white", line_width=1, row=2, col=1)
        fig2.update_layout(height=600, template="plotly_dark")
        st.plotly_chart(fig2, use_container_width=True)
        
        if not t.empty:
            t_show = t.copy()
            t_show['Duration'] = t_show['Duration'].apply(format_duration)
            st.dataframe(t_show.style.format({'PnL %': '{:.2f}', 'Entry ADF': '{:.4f}'}), use_container_width=True)
    else:
        st.warning("No data available for detailed chart")
else:
    st.info("👈 Select currency pairs, adjust settings, and click 'START BACKTEST'")
