import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Page configuration
st.set_page_config(page_title="Multi-Rating Stock Analysis App", layout="wide")

st.title("📊 Complete Stock & Dividend Scoring System")
st.caption("Independent Technical & Dividend Scores, Combined Score, and Buy/Sell Ratings.")

# Sidebar Input
ticker_input = st.sidebar.text_input("Enter Tickers (comma separated):", "O, MKC, AAPL, SCHD")
tickers = [t.strip().upper() for t in ticker_input.split(",") if t.strip()]

def get_rating(score):
    """Converts a 0-100 score into a standard rating scale"""
    if score >= 80:
        return "Strong Buy"
    elif score >= 65:
        return "Buy"
    elif score >= 45:
        return "Hold"
    elif score >= 30:
        return "Sell"
    else:
        return "Strong Sell"

def calculate_scores(ticker_symbol):
    """Calculates independent Technical and Dividend Scores, ratings, and combined metrics"""
    tk = yf.Ticker(ticker_symbol)
    df = tk.history(period="1y")
    
    if len(df) < 50:
        return None, "Insufficient historical price data"

    info = tk.info
    
    # ---------------------------------------------------------
    # Technical Indicators Setup
    # ---------------------------------------------------------
    df['EMA_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['EMA_50'] = df['Close'].ewm(span=50, adjust=False).mean()
    
    # RSI (14-period)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # ATR (14-period)
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()

    # Latest values
    latest = df.iloc[-1]
    price = latest['Close']
    ema20 = latest['EMA_20']
    ema50 = latest['EMA_50']
    rsi = latest['RSI']
    atr = latest['ATR']
    
    high_52w = df['High'].tail(252).max()
    low_52w = df['Low'].tail(252).min()
    pct_from_52w_high = ((high_52w - price) / high_52w) * 100

    # ---------------------------------------------------------
    # 1. TECHNICAL SCORE SYSTEM (100 Points Max)
    # ---------------------------------------------------------
    tech_score = 0
    tech_breakdown = {}

    # Trend (Max 40 pts)
    if price > ema20 > ema50:
        tech_score += 40
        tech_breakdown['Trend'] = "Strong Uptrend (+40)"
    elif price > ema20:
        tech_score += 25
        tech_breakdown['Trend'] = "Moderate Uptrend (+25)"
    else:
        tech_score += 0
        tech_breakdown['Trend'] = "Downtrend / Below EMAs (+0)"

    # RSI (Max 30 pts)
    if 50 <= rsi <= 65:
        tech_score += 30
        tech_breakdown['RSI'] = f"Ideal Bullish Range: {rsi:.1f} (+30)"
    elif 40 <= rsi < 50:
        tech_score += 20
        tech_breakdown['RSI'] = f"Neutral: {rsi:.1f} (+20)"
    elif rsi > 70:
        tech_score += 10
        tech_breakdown['RSI'] = f"Overbought (>70): {rsi:.1f} (+10)"
    else:
        tech_score += 0
        tech_breakdown['RSI'] = f"Weak / Oversold: {rsi:.1f} (+0)"

    # 52-Week High Proximity (Max 30 pts)
    if pct_from_52w_high <= 10:
        tech_score += 30
        tech_breakdown['52w Range'] = f"Within 10% of 52w High ({pct_from_52w_high:.1f}% off) (+30)"
    elif pct_from_52w_high <= 20:
        tech_score += 20
        tech_breakdown['52w Range'] = f"Within 20% of 52w High ({pct_from_52w_high:.1f}% off) (+20)"
    else:
        tech_score += 5
        tech_breakdown['52w Range'] = f">20% off 52w High ({pct_from_52w_high:.1f}% off) (+5)"

    # ---------------------------------------------------------
    # 2. DIVIDEND SCORE SYSTEM (100 Points Max)
    # ---------------------------------------------------------
    raw_yield = info.get('dividendYield', 0) or 0
    div_yield = raw_yield * 100 if raw_yield < 1 else raw_yield
    
    raw_payout = info.get('payoutRatio', 0) or 0
    payout_ratio = raw_payout * 100 if raw_payout < 1 else raw_payout
    
    div_score = 0
    div_breakdown = {}

    if div_yield == 0:
        div_breakdown['Dividend Yield'] = "No Dividend Paid (+0)"
        div_breakdown['Payout Safety'] = "N/A (+0)"
    else:
        # Dividend Yield (Max 50 pts)
        if div_yield >= 5.0:
            div_score += 50
            div_breakdown['Dividend Yield'] = f"High Yield: {div_yield:.2f}% (+50)"
        elif div_yield >= 3.0:
            div_score += 35
            div_breakdown['Dividend Yield'] = f"Moderate Yield: {div_yield:.2f}% (+35)"
        elif div_yield >= 1.5:
            div_score += 20
            div_breakdown['Dividend Yield'] = f"Low Yield: {div_yield:.2f}% (+20)"
        else:
            div_score += 10
            div_breakdown['Dividend Yield'] = f"Minimal Yield: {div_yield:.2f}% (+10)"

        # Payout Ratio Safety (Max 50 pts)
        if 20 <= payout_ratio <= 65:
            div_score += 50
            div_breakdown['Payout Safety'] = f"Optimal Safety Ratio: {payout_ratio:.1f}% (+50)"
        elif 65 < payout_ratio <= 80:
            div_score += 35
            div_breakdown['Payout Safety'] = f"Acceptable Ratio: {payout_ratio:.1f}% (+35)"
        elif payout_ratio < 20:
            div_score += 25
            div_breakdown['Payout Safety'] = f"Low Payout Ratio: {payout_ratio:.1f}% (+25)"
        elif 80 < payout_ratio <= 95:
            div_score += 15
            div_breakdown['Payout Safety'] = f"Elevated Risk: {payout_ratio:.1f}% (+15)"
        else:
            div_score += 0
            div_breakdown['Payout Safety'] = f"High Risk / Distressed: {payout_ratio:.1f}% (+0)"

    # ---------------------------------------------------------
    # 3. COMBINED METRICS AND RATINGS
    # ---------------------------------------------------------
    combined_score = round((tech_score + div_score) / 2, 1)

    tech_rating = get_rating(tech_score)
    div_rating = get_rating(div_score) if div_yield > 0 else "N/A"
    combined_rating = get_rating(combined_score)

    summary = {
        "Price": round(price, 2),
        "Tech Score": tech_score,
        "Tech Rating": tech_rating,
        "Div Score": div_score,
        "Div Rating": div_rating,
        "Combined Score": combined_score,
        "Combined Rating": combined_rating,
        "Dividend Yield": f"{div_yield:.2f}%" if div_yield > 0 else "N/A",
        "Payout Ratio": f"{payout_ratio:.1f}%" if div_yield > 0 else "N/A",
        "RSI": round(rsi, 2),
        "ATR": round(atr, 2),
        "EMA 20": round(ema20, 2),
        "EMA 50": round(ema50, 2),
        "Tech Breakdown": tech_breakdown,
        "Div Breakdown": div_breakdown
    }
    
    return summary, None

if st.sidebar.button("Run Stock Analysis"):
    results = []
    
    for ticker in tickers:
        metrics, error = calculate_scores(ticker)
        if error:
            st.warning(f"{ticker}: {error}")
            continue
            
        metrics["Ticker"] = ticker
        results.append(metrics)

    if results:
        # Sort results by combined score descending
        results = sorted(results, key=x: x["Combined Score"], reverse=True)
        
        st.subheader("📊 Stock Comparison & Rating Dashboard")
        table_data = [{
            "Ticker": r["Ticker"],
            "Combined Score / 100": r["Combined Score"],
            "Combined Rating": r["Combined Rating"],
            "Tech Score": r["Tech Score"],
            "Tech Rating": r["Tech Rating"],
            "Div Score": r["Div Score"],
            "Div Rating": r["Div Rating"],
            "Price": f"${r['Price']}",
            "Dividend Yield": r["Dividend Yield"],
            "Payout Ratio": r["Payout Ratio"],
            "RSI (14)": r["RSI"]
        } for r in results]
        
        st.dataframe(pd.DataFrame(table_data), use_container_width=True)

        # Detailed Breakdown Cards
        st.subheader("🔍 Detailed Breakdown & Individual Ratings")
        for r in results:
            with st.expander(f"{r['Ticker']} | Combined Rating: {r['Combined Rating']} ({r['Combined Score']}/100)"):
                col1, col2 = st.columns(2)
                
                with col1:
                    st.markdown(f"### 📈 Technical Rating: **{r['Tech Rating']}** ({r['Tech Score']}/100)")
                    for k, v in r["Tech Breakdown"].items():
                        st.write(f"- **{k}:** {v}")
                        
                with col2:
                    st.markdown(f"### 💰 Dividend Rating: **{r['Div Rating']}** ({r['Div Score']}/100)")
                    for k, v in r["Div Breakdown"].items():
                        st.write(f"- **{k}:** {v}")
