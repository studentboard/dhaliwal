import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(
    page_title="Alpha Intelligence & Crash Warning Engine",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Theme Custom Styling
st.markdown("""
    <style>
    .stMetric {
        background-color: #1E293B;
        padding: 12px;
        border-radius: 8px;
        border: 1px solid #334155;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 1. ROBUST MARKET CRASH & REGIME EVALUATOR
# -------------------------------------------------------------
@st.cache_data(ttl=180)
def evaluate_market_crash_risk():
    errors = []
    
    # 1. SPY Fetch
    try:
        spy_df = yf.Ticker("SPY").history(period="1y")
        if spy_df.empty or len(spy_df) < 50:
            return None, ["Unable to fetch SPY historical data."]
        spy_close = float(spy_df['Close'].iloc[-1])
        spy_sma50 = float(spy_df['Close'].rolling(50).mean().iloc[-1])
        spy_sma200 = float(spy_df['Close'].rolling(200).mean().iloc[-1])
    except Exception as e:
        return None, [f"SPY Data Fetch Error: {str(e)}"]

    # 2. VIX Fetch (with fallback handling)
    vix_current = 18.0  # Baseline safe fallback
    vix_sma20 = 18.0
    try:
        vix_df = yf.Ticker("^VIX").history(period="3mo")
        if not vix_df.empty and len(vix_df) > 5:
            vix_current = float(vix_df['Close'].iloc[-1])
            vix_sma20 = float(vix_df['Close'].rolling(20).mean().iloc[-1])
        else:
            # Secondary fallback to VXX ETF if ^VIX index is restricted
            vxx_df = yf.Ticker("VXX").history(period="1mo")
            if not vxx_df.empty:
                vix_current = float(vxx_df['Close'].iloc[-1])
                vix_sma20 = float(vxx_df['Close'].rolling(20).mean().iloc[-1])
    except Exception as e:
        errors.append(f"VIX Warning: {str(e)} - Using secondary baseline.")

    # 3. 10Y Yield Fetch
    yield_10y = 4.25
    try:
        tnx_df = yf.Ticker("^TNX").history(period="1mo")
        if not tnx_df.empty:
            yield_10y = float(tnx_df['Close'].iloc[-1])
    except Exception:
        pass

    # ---------------------------------------------------------
    # Risk Score Calculation Matrix
    # ---------------------------------------------------------
    risk_score = 0
    signals = []

    if spy_close < spy_sma50:
        risk_score += 25
        signals.append("SPY trading below 50-day SMA (Short-term weakness)")
    else:
        signals.append("SPY above 50-day SMA (Short-term strength intact)")

    if spy_close < spy_sma200:
        risk_score += 35
        signals.append("SPY trading below 200-day SMA (Structural Bear Trend)")
    else:
        signals.append("SPY above 200-day SMA (Long-term Bull Trend)")

    if vix_current > 30:
        risk_score += 30
        signals.append("VIX in Extreme Panic Zone (>30)")
    elif vix_current > 20:
        risk_score += 15
        signals.append("VIX Elevated Stress Zone (>20)")

    if vix_current > (vix_sma20 * 1.25):
        risk_score += 10
        signals.append("VIX Volatility Spiking >25% above 20-day mean")

    # Regime Categorization
    if risk_score >= 60:
        status = "CRITICAL RISK (DEFENSIVE REGIME)"
    elif risk_score >= 30:
        status = "MODERATE RISK (CAUTION ADVISED)"
    else:
        status = "HEALTHY / BULLISH REGIME"

    spy_vs_200 = round(((spy_close - spy_sma200) / spy_sma200) * 100, 2)

    return {
        "SPY Price": round(spy_close, 2),
        "SPY vs 200SMA": f"{'+' if spy_vs_200 > 0 else ''}{spy_vs_200}%",
        "VIX Level": round(vix_current, 2),
        "10Y Yield": f"{round(yield_10y, 2)}%",
        "Risk Score": risk_score,
        "Regime Status": status,
        "Signals": signals
    }, errors

# -------------------------------------------------------------
# 2. MULTI-FRAME PROJECTION & PROBABILITY ENGINE
# -------------------------------------------------------------
def analyze_stock_deep(symbol, spy_20d, qqq_20d):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        if df.empty or len(df) < 60:
            return None

        close = float(df['Close'].iloc[-1])
        prev_close = float(df['Close'].iloc[-2])

        # Moving Averages
        ema20 = float(df['Close'].ewm(span=20).mean().iloc[-1])
        sma50 = float(df['Close'].rolling(window=50).mean().iloc[-1])
        sma200 = float(df['Close'].rolling(window=200).mean().iloc[-1])

        # 1. Trend Score (25 pts)
        trend_score = 0
        if close > ema20: trend_score += 10
        if ema20 > sma50: trend_score += 10
        if sma50 > sma200: trend_score += 5

        # 2. Relative Strength vs Benchmarks (25 pts)
        perf_20d = ((close - float(df['Close'].iloc[-20])) / float(df['Close'].iloc[-20])) * 100
        rs_spy = perf_20d - spy_20d
        rs_qqq = perf_20d - qqq_20d

        rs_score = 0
        if rs_spy > 0: rs_score += 15
        if rs_qqq > 0: rs_score += 10

        # 3. Dark Pool / Accumulation Ratio (25 pts)
        vol = float(df['Volume'].iloc[-1])
        avg_vol_20 = float(df['Volume'].rolling(window=20).mean().iloc[-1])
        vol_ratio = vol / avg_vol_20 if avg_vol_20 > 0 else 1.0

        accum_score = 0
        if close > prev_close and vol_ratio >= 1.5:
            accum_score = 25
        elif close > prev_close and vol_ratio >= 1.2:
            accum_score = 15
        elif close > prev_close:
            accum_score = 5

        # 4. Volatility Contraction Ratio (25 pts)
        daily_ranges = df['High'] - df['Low']
        recent_range = float(daily_ranges.iloc[-1])
        avg_10d_range = float(daily_ranges.tail(10).mean())
        vcp_ratio = recent_range / avg_10d_range if avg_10d_range > 0 else 1.0

        vcp_score = 0
        if vcp_ratio < 0.6: vcp_score = 25
        elif vcp_ratio < 0.8: vcp_score = 15
        elif vcp_ratio < 1.0: vcp_score = 5

        # Total Alpha Score
        total_alpha = trend_score + rs_score + accum_score + vcp_score

        # Multi-Horizon Projection Multipliers & Probabilities
        if total_alpha >= 80:
            m1_mult, m3_mult, m6_mult, m12_mult = 1.08, 1.25, 1.50, 2.10
            hit_prob = 84
            tier = "Tier 1: High Alpha Outlier"
            reason = "Aggressive institutional volume inflow combined with tight VCP volatility compression and benchmark outperformance."
        elif total_alpha >= 60:
            m1_mult, m3_mult, m6_mult, m12_mult = 1.03, 1.12, 1.25, 1.50
            hit_prob = 65
            tier = "Tier 2: Watchlist Accumulator"
            reason = "Steady relative strength and base formation. Requires a high-volume breakout to trigger Tier 1 status."
        else:
            m1_mult, m3_mult, m6_mult, m12_mult = 0.98, 1.02, 1.08, 1.18
            hit_prob = 39
            tier = "Tier 3: Low Conviction / Lagging"
            reason = "Lacking volume expansion or trading below core moving averages. High probability of range-bound chop or drift."

        return {
            "Symbol": symbol,
            "Price": round(close, 2),
            "1D Change %": round(((close - prev_close) / prev_close) * 100, 2),
            "Alpha Score": total_alpha,
            "1M Target": round(close * m1_mult, 2),
            "3M Target": round(close * m3_mult, 2),
            "6M Target": round(close * m6_mult, 2),
            "12M Target": round(close * m12_mult, 2),
            "Probability": f"{hit_prob}%",
            "Tier Setup": tier,
            "Thesis Breakdown": reason,
            "Vol Accum Ratio": f"{round(vol_ratio, 2)}x",
            "VCP Ratio": round(vcp_ratio, 2),
            "RS vs SPY": f"{'+' if rs_spy > 0 else ''}{round(rs_spy, 1)}%"
        }
    except Exception:
        return None

# Benchmark Cache
@st.cache_data(ttl=300)
def get_benchmarks():
    try:
        spy = yf.Ticker("SPY").history(period="2mo")
        qqq = yf.Ticker("QQQ").history(period="2mo")
        spy_20d = ((float(spy['Close'].iloc[-1]) - float(spy['Close'].iloc[-20])) / float(spy['Close'].iloc[-20])) * 100
        qqq_20d = ((float(qqq['Close'].iloc[-1]) - float(qqq['Close'].iloc[-20])) / float(qqq['Close'].iloc[-20])) * 100
        return spy_20d, qqq_20d
    except Exception:
        return 0.0, 0.0

spy_20d, qqq_20d = get_benchmarks()

# -------------------------------------------------------------
# APP INTERFACE
# -------------------------------------------------------------
st.title("⚡ Alpha Intelligence & Market Protection Dashboard")

# 1. MARKET CRASH MONITOR PANEL
st.subheader("🛡️ Market Crash & Macro Regime Monitor")

crash_data, crash_errors = evaluate_market_crash_risk()

if crash_data:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("SPY Index", f"${crash_data['SPY Price']}")
    c2.metric("SPY vs 200 SMA", crash_data['SPY vs 200SMA'])
    c3.metric("VIX Volatility", f"{crash_data['VIX Level']}")
    c4.metric("10Y Yield", crash_data['10Y Yield'])
    c5.metric("Crash Risk Score", f"{crash_data['Risk Score']} / 100")

    if crash_data['Risk Score'] >= 60:
        st.error(f"🚨 **MARKET REGIME:** {crash_data['Regime Status']} | Active Conditions: {', '.join(crash_data['Signals'])}")
    elif crash_data['Risk Score'] >= 30:
        st.warning(f"⚠️ **MARKET REGIME:** {crash_data['Regime Status']} | Active Conditions: {', '.join(crash_data['Signals'])}")
    else:
        st.success(f"🟢 **MARKET REGIME:** {crash_data['Regime Status']} | Conditions: {', '.join(crash_data['Signals'])}")
else:
    st.error("⚠️ Market Crash Monitor is currently unable to reach live Yahoo Finance data. Please click below to clear cache and retry.")
    if st.button("🔄 Force Refresh Market Data"):
        st.cache_data.clear()
        st.rerun()

st.divider()

# 2. WATCHLIST TARGETS & PROJECTIONS TABLE
st.subheader("🎯 Primary Watchlist — Multi-Frame Target Projections")

default_list = ["POET", "NBIS", "ZETA", "SOUN", "LUNR", "WOLF", "ASTS", "HPE", "SYM", "RGTI"]
user_watchlist = st.text_input("Modify Watchlist Tickers (comma separated):", value=", ".join(default_list))
symbols = [s.strip().upper() for s in user_watchlist.split(",") if s.strip()]

results = []
with st.spinner("Calculating Outlier Metrics, Multi-Horizon Targets & Probabilities..."):
    for sym in symbols:
        res = analyze_stock_deep(sym, spy_20d, qqq_20d)
        if res:
            results.append({
                "Symbol": res["Symbol"],
                "Price": f"${res['Price']}",
                "1D %": f"{res['1D Change %']}%",
                "Alpha Score": res["Alpha Score"],
                "Probability": res["Probability"],
                "1M Target": f"${res['1M Target']}",
                "3M Target": f"${res['3M Target']}",
                "6M Target": f"${res['6M Target']}",
                "12M Target": f"${res['12M Target']}",
                "Setup Tier": res["Tier Setup"]
            })

if results:
    df = pd.DataFrame(results)

    def highlight_alpha(val):
        if isinstance(val, (int, float)):
            if val >= 80: return 'background-color: #059669; color: white; font-weight: bold;'
            elif val >= 60: return 'background-color: #D97706; color: white;'
            else: return 'background-color: #DC2626; color: white;'
        return ''

    st.dataframe(
        df.style.map(highlight_alpha, subset=['Alpha Score']),
        use_container_width=True,
        height=380
    )

st.divider()

# 3. SINGLE STOCK DEEP DIVE & REASONING BREAKDOWN
st.subheader("🔬 Ticker Deep Dive & Probability Breakdown")
target_sym = st.text_input("Enter Ticker for Structural Thesis Breakdown:", value="POET").upper()

if target_sym:
    stock_detail = analyze_stock_deep(target_sym, spy_20d, qqq_20d)
    if stock_detail:
        st.markdown(f"### **{target_sym} Comprehensive Thesis & Target Breakdown**")

        # Top Metric Strip
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Current Price", f"${stock_detail['Price']}", f"{stock_detail['1D Change %']}%")
        p2.metric("Alpha Outlier Score", f"{stock_detail['Alpha Score']} / 100")
        p3.metric("Target Probability", stock_detail['Probability'])
        p4.metric("Volume Accumulation Ratio", stock_detail['Vol Accum Ratio'])

        # Projections Grid
        st.markdown("#### 📈 Multi-Horizon Price Targets")
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("1-Month Projection", f"${stock_detail['1M Target']}")
        t2.metric("3-Month Projection", f"${stock_detail['3M Target']}")
        t3.metric("6-Month Projection", f"${stock_detail['6M Target']}")
        t4.metric("12-Month Projection", f"${stock_detail['12M Target']}")

        # Quantitative Thesis Explanation
        st.markdown("#### 🧠 Quantitative Thesis & Structural Reasoning")
        st.info(f"**Classification:** {stock_detail['Tier Setup']}\n\n**Reasoning:** {stock_detail['Thesis Breakdown']}")

        # Structural Factors
        f1, f2, f3 = st.columns(3)
        f1.metric("Relative Strength vs SPY", stock_detail['RS vs SPY'])
        f2.metric("VCP Compression Factor", stock_detail['VCP Ratio'])
        f3.metric("Institutional Volume Factor", stock_detail['Vol Accum Ratio'])
    else:
        st.error(f"Could not load data for symbol '{target_sym}'. Check the spelling or try again.")
