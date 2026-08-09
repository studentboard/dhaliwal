import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Alpha Outlier Engine", layout="wide")

st.title("🚀 Multi-Bagger Alpha Outlier Dashboard")
st.caption("Live System Tracking & Outlier Potential Evaluator")

# -------------------------------------------------------------
# 1. CORE EVALUATION ENGINE
# -------------------------------------------------------------
def analyze_ticker(symbol, spx_perf):
    try:
        ticker = yf.Ticker(symbol)
        df = ticker.history(period="6m")
        if df.empty or len(df) < 50:
            return None
        
        close = df['Close'].iloc[-1]
        prev_close = df['Close'].iloc[-2]
        ema20 = df['Close'].ewm(span=20).mean().iloc[-1]
        sma50 = df['Close'].rolling(window=50).mean().iloc[-1]
        vol = df['Volume'].iloc[-1]
        avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
        
        # 1. Trend Check
        uptrend = (close > ema20) and (ema20 > sma50)
        
        # 2. Relative Strength vs SPY (20-day)
        stock_perf = ((close - df['Close'].iloc[-20]) / df['Close'].iloc[-20]) * 100
        rs_delta = stock_perf - spx_perf
        
        # 3. Accumulation / Volume Surge
        accumulation = (close > prev_close) and (vol > avg_vol * 1.25)
        
        # 4. Volatility Contraction Pattern (VCP)
        daily_range = df['High'] - df['Low']
        vcp = daily_range.iloc[-1] < (daily_range.tail(10).mean() * 0.7)
        
        # Calculate Alpha Score
        score = 40
        if uptrend: score += 20
        if rs_delta > 0: score += 20
        if accumulation: score += 10
        if vcp: score += 10
        
        return {
            "Symbol": symbol,
            "Price": round(close, 2),
            "1D Change %": round(((close - prev_close) / prev_close) * 100, 2),
            "Alpha Score": score,
            "Trend": "🟢 BULL" if uptrend else "🔴 BEAR",
            "RS vs SPY": f"{round(rs_delta, 1)}%",
            "Setup": "⚡ VCP" if vcp else ("🔋 ACCUM" if accumulation else "⚪ IDLE")
        }
    except Exception:
        return None

# Fetch Benchmark SPY Data
spy = yf.Ticker("SPY").history(period="1mo")
spy_perf = ((spy['Close'].iloc[-1] - spy['Close'].iloc[-20]) / spy['Close'].iloc[-20]) * 100

# -------------------------------------------------------------
# 2. WATCHLIST AUTOMATION
# -------------------------------------------------------------
st.subheader("📊 Top High-Alpha Watchlist")

default_watchlist = ["POET", "NBIS", "ZETA", "SOUN", "LUNR", "WOLF", "ASTS", "HPE", "SYM", "RGTI"]
custom_list = st.text_input("Customize Watchlist (comma separated):", value=", ".join(default_watchlist))
watchlist = [s.strip().upper() for s in custom_list.split(",") if s.strip()]

results = []
with st.spinner("Scanning market data..."):
    for sym in watchlist:
        res = analyze_ticker(sym, spy_perf)
        if res:
            results.append(res)

if results:
    df_results = pd.DataFrame(results)

    def color_score(val):
        if val >= 80: return 'background-color: #10B981; color: black; font-weight: bold;'
        elif val >= 60: return 'background-color: #EAB308; color: black;'
        else: return 'background-color: #EF4444; color: white;'

    st.dataframe(df_results.style.map(color_score, subset=['Alpha Score']), use_container_width=True)

st.divider()

# -------------------------------------------------------------
# 3. SINGLE-STOCK OUTLIER ANALYZER
# -------------------------------------------------------------
st.subheader("🔍 Evaluate Any Stock for Multi-Bagger Potential")
user_input = st.text_input("Enter Ticker Symbol to Grade:", value="QQQ").upper()

if user_input:
    single_res = analyze_ticker(user_input, spy_perf)
    if single_res:
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Current Price", f"${single_res['Price']}", f"{single_res['1D Change %']}%")
        c2.metric("Alpha Score", f"{single_res['Alpha Score']}/100")
        c3.metric("Trend Structure", single_res['Trend'])
        c4.metric("Setup Status", single_res['Setup'])
        
        if single_res['Alpha Score'] >= 80:
            st.success("🔥 **High Outlier Potential:** Strong uptrend with outperformance and volume backing.")
        elif single_res['Alpha Score'] >= 60:
            st.warning("⚠️ **Watchlist Candidate:** Consolidating or building a base.")
        else:
            st.error("❌ **Low Outlier Conviction:** Weak trend or lagging relative strength.")
    else:
        st.error("Could not fetch data for this symbol.")
