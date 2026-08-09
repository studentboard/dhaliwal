import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Alpha Outlier Intelligence Engine", layout="wide")

# Dark / Quantitative Styling
st.markdown("""
    <style>
    .metric-card {
        background-color: #1E293B;
        padding: 15px;
        border-radius: 10px;
        border: 1px solid #334155;
    }
    </style>
""", unsafe_allow_html=True)

st.title("⚡ Alpha Outlier & Dark-Pool Intelligence Engine")
st.caption("Live Quantitative Screening | Relative Strength, VCP Compression & Outlier Valuation Engine")

# -------------------------------------------------------------
# 1. ADVANCED MULTI-BAGGER QUANT ENGINE
# -------------------------------------------------------------
def analyze_stock_full(symbol, spy_20d, qqq_20d):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        if df.empty or len(df) < 100:
            return None
        
        close = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]
        
        # Moving Averages & Trend Filters
        ema20 = df['Close'].ewm(span=20).mean().iloc[-1]
        sma50 = df['Close'].rolling(window=50).mean().iloc[-1]
        sma200 = df['Close'].rolling(window=200).mean().iloc[-1]
        
        # 1. Trend Structure Score (Max 25 pts)
        trend_score = 0
        if close > ema20: trend_score += 10
        if ema20 > sma50: trend_score += 10
        if sma50 > sma200: trend_score += 5
        
        # 2. Relative Strength vs SPY & QQQ (Max 25 pts)
        perf_20d = ((close - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) * 100
        rs_spy = perf_20d - spy_20d
        rs_qqq = perf_20d - qqq_20d
        
        rs_score = 0
        if rs_spy > 0: rs_score += 15
        if rs_qqq > 0: rs_score += 10
        
        # 3. Dark Pool / Volume Accumulation Multiplier (Max 25 pts)
        vol = df['Volume'].iloc[-1]
        avg_vol_20 = df['Volume'].rolling(window=20).mean().iloc[-1]
        vol_ratio = vol / avg_vol_20 if avg_vol_20 > 0 else 1.0
        
        accum_score = 0
        if close > prev_close and vol_ratio >= 1.5:
            accum_score = 25
        elif close > prev_close and vol_ratio >= 1.2:
            accum_score = 15
        elif close > prev_close:
            accum_score = 5
            
        # 4. Volatility Contraction Pattern (VCP Compression Ratio) (Max 25 pts)
        daily_ranges = df['High'] - df['Low']
        recent_range = daily_ranges.iloc[-1]
        avg_10d_range = daily_ranges.tail(10).mean()
        vcp_ratio = recent_range / avg_10d_range if avg_10d_range > 0 else 1.0
        
        vcp_score = 0
        if vcp_ratio < 0.6:
            vcp_score = 25  # High Compression / Tight Base
        elif vcp_ratio < 0.8:
            vcp_score = 15
        elif vcp_ratio < 1.0:
            vcp_score = 5
            
        # Total Alpha Score (0 - 100)
        total_alpha = trend_score + rs_score + accum_score + vcp_score
        
        # 12-Month Target Projections based on Outlier Alpha Score
        if total_alpha >= 80:
            target_mult = 2.2  # 120% potential return
        elif total_alpha >= 60:
            target_mult = 1.5  # 50% potential return
        else:
            target_mult = 1.15 # 15% standard growth
            
        target_price_12m = close * target_mult
        
        return {
            "Symbol": symbol,
            "Price": round(close, 2),
            "1D Change %": round(((close - prev_close) / prev_close) * 100, 2),
            "Alpha Score": total_alpha,
            "Trend Structure": f"{trend_score}/25",
            "RS Alpha (SPY/QQQ)": f"+{round(rs_spy, 1)}%",
            "Vol Accum Ratio": f"{round(vol_ratio, 2)}x",
            "VCP Compression": f"{round(vcp_ratio, 2)}",
            "12M Target": f"${round(target_price_12m, 2)}"
        }
    except Exception as e:
        return None

# Fetch Benchmarks (SPY & QQQ 20-Day Performance)
@st.cache_data(ttl=300)
def get_benchmarks():
    spy = yf.Ticker("SPY").history(period="2mo")
    qqq = yf.Ticker("QQQ").history(period="2mo")
    spy_20d = ((spy['Close'].iloc[-1] - spy['Close'].iloc[-20]) / spy['Close'].iloc[-20]) * 100
    qqq_20d = ((qqq['Close'].iloc[-1] - qqq['Close'].iloc[-20]) / qqq['Close'].iloc[-20]) * 100
    return spy_20d, qqq_20d

spy_20d, qqq_20d = get_benchmarks()

# -------------------------------------------------------------
# 2. WATCHLIST DEPLOYMENT TABLE
# -------------------------------------------------------------
st.subheader("🎯 Primary High-Alpha Focus Watchlist")

default_list = ["POET", "NBIS", "ZETA", "SOUN", "LUNR", "WOLF", "ASTS", "HPE", "SYM", "RGTI"]
user_watchlist = st.text_input("Modify Watchlist (comma separated):", value=", ".join(default_list))
symbols = [s.strip().upper() for s in user_watchlist.split(",") if s.strip()]

results = []
with st.spinner("Executing Full Alpha & Dark Pool Scan..."):
    for sym in symbols:
        res = analyze_stock_full(sym, spy_20d, qqq_20d)
        if res:
            results.append(res)

if results:
    df = pd.DataFrame(results)

    def highlight_alpha(val):
        if val >= 80: return 'background-color: #059669; color: white; font-weight: bold;'
        elif val >= 60: return 'background-color: #D97706; color: white;'
        else: return 'background-color: #DC2626; color: white;'

    st.dataframe(
        df.style.map(highlight_alpha, subset=['Alpha Score']),
        use_container_width=True,
        height=400
    )

st.divider()

# -------------------------------------------------------------
# 3. SINGLE-TICKER DEEP DECONSTRUCTION
# -------------------------------------------------------------
st.subheader("🔬 Single-Stock Multi-Bagger Breakdown")
target_symbol = st.text_input("Enter Ticker for Full Analysis:", value="POET").upper()

if target_symbol:
    single = analyze_stock_full(target_symbol, spy_20d, qqq_20d)
    if single:
        m1, m2, m3, m4, m5 = st.columns(5)
        m1.metric("Current Price", f"${single['Price']}", f"{single['1D Change %']}%")
        m2.metric("Total Alpha Score", f"{single['Alpha Score']} / 100")
        m3.metric("RS vs SPY Delta", single['RS Alpha (SPY/QQQ)'])
        m4.metric("Volume Accumulation", single['Vol Accum Ratio'])
        m5.metric("12M Target Projection", single['12M Target'])
        
        st.markdown("### 📊 Factor Breakdown Breakdown")
        col_a, col_b, col_c, col_d = st.columns(4)
        col_a.info(f"**Trend Component:** {single['Trend Structure']}")
        col_b.info(f"**Relative Strength:** {single['RS Alpha (SPY/QQQ)']}")
        col_c.info(f"**Volume Accumulation:** {single['Vol Accum Ratio']}")
        col_d.info(f"**VCP Compression:** {single['VCP Compression']}")
        
        if single['Alpha Score'] >= 80:
            st.success("🔥 **TIER 1 MULTI-BAGGER SETUP:** Stock exhibits strong trend alignment, heavy accumulation, and significant relative strength.")
        elif single['Alpha Score'] >= 60:
            st.warning("⚡ **TIER 2 WATCHLIST SETUP:** Building a compression base or consolidating. Monitor for volume breakout.")
        else:
            st.error("⚠️ **LOW CONVICTION SETUP:** Lacks relative strength or institutional volume backing at present.")
    else:
        st.error(f"Unable to retrieve full market data for {target_symbol}.")
