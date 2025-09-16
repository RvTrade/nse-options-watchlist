import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="NSE Options Watchlist", layout="wide")

st.title("📈 NSE Options Watchlist (Demo Version)")

# -------------------------------
# Stock list (you can expand this)
# -------------------------------
stocks = ["RELIANCE.NS", "TCS.NS", "INFY.NS", "HDFCBANK.NS", "ICICIBANK.NS"]

@st.cache_data
def get_stock_data(ticker):
    try:
        df = yf.download(ticker, period="6mo", interval="1d")
        if df.empty:
            return None
        df["Ticker"] = ticker
        return df
    except Exception as e:
        st.error(f"❌ Error fetching {ticker}: {e}")
        return None

# -------------------------------
# Fetch all stock data
# -------------------------------
data_frames = []
for stock in stocks:
    df = get_stock_data(stock)
    if df is not None:
        data_frames.append(df)

if not data_frames:
    st.error("⚠️ Could not fetch any stock data. Try again later.")
    st.stop()

df = pd.concat(data_frames)

# -------------------------------
# Add custom indicators
# -------------------------------
try:
    df["Daily Return"] = df["Adj Close"].pct_change()
    df["Volatility"] = df["Daily Return"].rolling(window=20).std()
    df["Opportunity Score"] = (df["Daily Return"] * 100) / (df["Volatility"] + 1e-6)
except Exception as e:
    st.error(f"⚠️ Error creating indicators: {e}")

# -------------------------------
# Display data safely
# -------------------------------
st.subheader("📊 Raw Stock Data (last 10 rows)")
st.dataframe(df.tail(10))

# Top opportunities
if "Opportunity Score" in df.columns and not df["Opportunity Score"].isnull().all():
    top_stocks = df.sort_values(by="Opportunity Score", ascending=False).head(5)
    st.subheader("🚀 Top 5 Option Opportunities")
    st.dataframe(top_stocks[["Ticker", "Adj Close", "Daily Return", "Volatility", "Opportunity Score"]])
else:
    st.warning("⚠️ No valid Opportunity Score found. Data may be missing or incomplete.")

# -------------------------------
# Interactive section
# -------------------------------
selected_ticker = st.selectbox("🔎 Select a stock to view details", stocks)

stock_df = df[df["Ticker"] == selected_ticker]
if not stock_df.empty:
    st.line_chart(stock_df["Adj Close"], use_container_width=True)
else:
    st.warning(f"⚠️ No data available for {selected_ticker}")