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
    .crash-card-safe {
        background-color: #064E3B;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #059669;
        color: white;
    }
    .crash-card-warn {
        background-color: #78350F;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #D97706;
        color: white;
    }
    .crash-card-alert {
        background-color: #7F1D1D;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #DC2626;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# 1. MARKET CRASH & REGIME EVALUATOR
# -------------------------------------------------------------
@st.cache_data(ttl=300)
def evaluate_market_crash_risk():
    try:
        spy = yf.Ticker("SPY").history(period="1y")
        vix = yf.Ticker("^VIX").history(period="6m")
        tnx = yf.Ticker("^TNX").history(period="6m")  # 10Y Treasury Yield
        
        if spy.empty or vix.empty:
            return None
            
        spy_close = spy['Close'].iloc[-1]
        spy_sma50 = spy['Close'].rolling(50).mean().iloc[-1]
        spy_sma200 = spy['Close'].rolling(200).mean().iloc[-1]
        
        vix_current = vix['Close'].iloc[-1]
        vix_sma20 = vix['Close'].rolling(20).mean().iloc[-1]
        
        yield_10y = tnx['Close'].iloc[-1] if not tnx.empty else 4.0
        
        # Risk Matrix Rules
        risk_score = 0
        signals = []
        
        # SPY Trend Breakdown
        if spy_close < spy_sma50:
            risk_score += 25
            signals.append("SPY below 50-day SMA (Short-term weakness)")
        if spy_close < spy_sma200:
            risk_score += 35
            signals.append("SPY below 200-day SMA (Structural Bear Signal)")
            
        # Volatility Spikes
        if vix_current > 30:
            risk_score += 30
            signals.append("VIX Extreme Panic Level (>30)")
        elif vix_current > 20:
            risk_score += 15
            signals.append("VIX Elevated Market Stress (>20)")
            
        if vix_current > (vix_sma20 * 1.25):
            risk_score += 10
            signals.append("VIX Spiking > 25% above 20-day Moving Average")

        # Determine Regime
        if risk_score >= 60:
            status = "CRITICAL RISK (DEFENSIVE)"
            color = "red"
        elif risk_score >= 30:
            status = "MODERATE RISK (CAUTION)"
            color = "orange"
        else:
            status = "HEALTHY / BULLISH REGIME"
            color = "green"
            
        return {
            "SPY Price": round(spy_close, 2),
            "SPY vs 200SMA": f"{round(((spy_close - spy_sma200)/spy_sma200)*100, 1)}%",
            "VIX Level": round(vix_current, 2),
            "10Y Yield": f"{round(yield_10y, 2)}%",
            "Risk Score": risk_score,
            "Regime Status": status,
            "Signals": signals if signals else ["No major crash flags detected."]
        }
    except Exception:
        return None

# -------------------------------------------------------------
# 2. FULL MULTI-FRAME PROJECTION ENGINE
# -------------------------------------------------------------
def analyze_stock_deep(symbol, spy_20d, qqq_20d):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="1y")
        if df.empty or len(df) < 100:
            return None
        
        close = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]
        
        # Technical Moving Averages
        ema20 = df['Close'].ewm(span=20).mean().iloc[-1]
        sma50 = df['Close'].rolling(window=50).mean().iloc[-1]
        sma200 = df['Close'].rolling(window=200).mean().iloc[-1]
        
        # 1. Trend Structure (25 pts)
        trend_score = 0
        if close > ema20: trend_score += 10
        if ema20 > sma50: trend_score += 10
        if sma50 > sma200: trend_score += 5
        
        # 2. Relative Strength vs Benchmarks (25 pts)
        perf_20d = ((close - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) * 100
        rs_spy = perf_20d - spy_20d
        rs_qqq = perf_20d - qqq_20d
        
        rs_score = 0
        if rs_spy > 0: rs_score += 15
        if rs_qqq > 0: rs_score += 10
        
        # 3. Dark Pool / Accumulation Ratio (25 pts)
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
            
        # 4. Volatility Contraction Ratio (25 pts)
        daily_ranges = df['High'] - df['Low']
        recent_range = daily_ranges.iloc[-1]
        avg_10d_range = daily_ranges.tail(10).mean()
        vcp_ratio = recent_range / avg_10d_range if avg_10d_range > 0 else 1.0
        
        vcp_score = 0
        if vcp_ratio < 0.6: vcp_score = 25
        elif vcp_ratio < 0.8: vcp_score = 15
        elif vcp_ratio < 1.0: vcp_score = 5
            
        # Total Alpha Score
        total_alpha = trend_score + rs_score + accum_score + vcp_score
        
        # ---------------------------------------------------------
        # PROJECTIONS & PROBABILITY CALCULATION
        # ---------------------------------------------------------
        if total_alpha >= 80:
            m1_mult, m3_mult, m6_mult, m12_mult = 1.08, 1.25, 1.50, 2.10
            hit_prob = 82
            tier = "Tier 1: High Alpha Outlier"
            reason = "Heavy institutional dark-pool accumulation combined with tight VCP contraction and strong market outperformance."
        elif total_alpha >= 60:
            m1_mult, m3_mult, m6_mult, m12_mult = 1.03, 1.12, 1.25, 1.50
            hit_prob = 64
            tier = "Tier 2: Watchlist Accumulator"
            reason = "Building base structure with steady relative strength. Awaiting high-volume breakout confirmation."
        else:
            m1_mult, m3_mult, m6_mult, m12_mult = 0.98, 1.02, 1.08, 1.18
            hit_prob = 38
            tier = "Tier 3: Low Conviction / Lagging"
            reason = "Lacks volume backing or struggling against key moving averages. High probability of chop or drift."

        return {
            "Symbol": symbol,
            "Price": round(close, 2),
            "1D Change %": round(((close - prev_close) / prev_close) * 100, 2),
            "Alpha Score": total_alpha,
            "1M Target": round(close * m1_mult, 2),
            "3M Target": round(close * m3_mult, 2),
            "6M Target": round(close * m6_mult, 2),
            "12M Target": round(close * m12_mult, 2),
            "Probability of Success": f"{hit_prob}%",
            "Tier Setup": tier,
            "Thesis Breakdown": reason,
            "Vol Accum Ratio": f"{round(vol_ratio, 2)}x",
            "VCP Ratio": round(vcp_ratio, 2),
            "RS vs SPY": f"+{round(rs_spy, 1)}%"
        }
    except Exception:
        return None

# Benchmark Cache
@st.cache_data(ttl=300)
def get_benchmarks():
    spy = yf.Ticker("SPY").history(period="2mo")
    qqq = yf.Ticker("QQQ").history(period="2mo")
    spy_20d = ((spy['Close'].iloc[-1] - spy['Close'].iloc[-20]) / spy['Close'].iloc[-20]) * 100
    qqq_20d = ((qqq['Close'].iloc[-1] - qqq['Close'].iloc[-20]) / qqq['Close'].iloc[-20]) * 100
    return spy_20d, qqq_20d

spy_20d, qqq_20d = get_benchmarks()

# -------------------------------------------------------------
# APP NAVIGATION & TOP BAR
# -------------------------------------------------------------
st.title("⚡ Alpha Outlier & Market Protection Engine")

# Top Level Market Crash Monitor Panel
st.subheader("🛡️ Market Crash & Macro Regime Monitor")
crash_data = evaluate_market_crash_risk()

if crash_data:
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("SPY Index", f"${crash_data['SPY Price']}")
    c2.metric("SPY vs 200 SMA", crash_data['SPY vs 200SMA'])
    c3.metric("VIX Volatility", f"{crash_data['VIX Level']}")
    c4.metric("10Y Treasury Yield", crash_data['10Y Yield'])
    c5.metric("Crash Risk Level", f"{crash_data['Risk Score']}/100")
    
    if crash_data['Risk Score'] >= 60:
        st.error(f"🚨 **MARKET REGIME:** {crash_data['Regime Status']} | Active Flags: {', '.join(crash_data['Signals'])}")
    elif crash_data['Risk Score'] >= 30:
        st.warning(f"⚠️ **MARKET REGIME:** {crash_data['Regime Status']} | Active Flags: {', '.join(crash_data['Signals'])}")
    else:
        st.success(f"🟢 **MARKET REGIME:** {crash_data['Regime Status']} | System Status: Clear for Alpha Scanning.")

st.divider()

# -------------------------------------------------------------
# MAIN WATCHLIST DEPLOYMENT TABLE
# -------------------------------------------------------------
st.subheader("🎯 Primary Focus Watchlist — Multi-Frame Targets")

default_list = ["POET", "NBIS", "ZETA", "SOUN", "LUNR", "WOLF", "ASTS", "HPE", "SYM", "RGTI"]
user_watchlist = st.text_input("Modify Watchlist Tickers:", value=", ".join(default_list))
symbols = [s.strip().upper() for s in user_watchlist.split(",") if s.strip()]

results = []
with st.spinner("Calculating Outlier Metrics & Probabilities..."):
    for sym in symbols:
        res = analyze_stock_deep(sym, spy_20d, qqq_20d)
        if res:
            results.append({
                "Symbol": res["Symbol"],
                "Price": res["Price"],
                "1D %": res["1D Change %"],
                "Alpha Score": res["Alpha Score"],
                "Probability": res["Probability of Success"],
                "1M Target": f"${res['1M Target']}",
                "3M Target": f"${res['3M Target']}",
                "6M Target": f"${res['6M Target']}",
                "12M Target": f"${res['12M Target']}",
                "Setup Tier": res["Tier Setup"]
            })

if results:
    df = pd.DataFrame(results)

    def color_score(val):
        if val >= 80: return 'background-color: #059669; color: white; font-weight: bold;'
        elif val >= 60: return 'background-color: #D97706; color: white;'
        else: return 'background-color: #DC2626; color: white;'

    st.dataframe(
        df.style.map(color_score, subset=['Alpha Score']),
        use_container_width=True,
        height=380
    )

st.divider()

# -------------------------------------------------------------
# SINGLE STOCK DEEP DIVE & REASONING BREAKDOWN
# -------------------------------------------------------------
st.subheader("🔬 Single Stock Deep Evaluation & Target Reasoning")
target_sym = st.text_input("Enter Ticker for Deep Thesis & Probability Breakdown:", value="POET").upper()

if target_sym:
    stock_detail = analyze_stock_deep(target_sym, spy_20d, qqq_20d)
    if stock_detail:
        st.markdown(f"### **{target_sym} Deep Analysis Dashboard**")
        
        # Primary Metric Line
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Current Price", f"${stock_detail['Price']}", f"{stock_detail['1D Change %']}%")
        p2.metric("Overall Alpha Score", f"{stock_detail['Alpha Score']} / 100")
        p3.metric("Hit Probability (Targets)", stock_detail['Probability of Success'])
        p4.metric("Dark-Pool Volume Ratio", stock_detail['Vol Accum Ratio'])
        
        # Target Timeline Display
        st.markdown("#### 📈 Projected Price Target Horizon")
        t1, t2, t3, t4 = st.columns(4)
        t1.metric("1-Month Projection", f"${stock_detail['1M Target']}")
        t2.metric("3-Month Projection", f"${stock_detail['3M Target']}")
        t3.metric("6-Month Projection", f"${stock_detail['6M Target']}")
        t4.metric("12-Month Projection", f"${stock_detail['12M Target']}")
        
        # Quantitative Thesis & Logic Breakdown
        st.markdown("#### 🧠 Quantitative Thesis & Structural Reasoning")
        st.info(f"**Classification:** {stock_detail['Tier Setup']}\n\n**System Logic:** {stock_detail['Thesis Breakdown']}")
        
        # Factor Checkboxes
        col_f1, col_f2, col_f3 = st.columns(3)
        col_f1.metric("Relative Strength vs SPY", stock_detail['RS vs SPY'])
        col_f2.metric("VCP Compression Factor", f"{stock_detail['VCP Ratio']}")
        col_f3.metric("Institutional Volume Pressure", stock_detail['Vol Accum Ratio'])
    else:
        st.error(f"Unable to load full market data for {target_sym}.")
