import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import time
import smtplib
from email.message import EmailMessage

# -----------------------
# Helper Functions
# -----------------------
def fetch_stock_data(ticker):
    stock = yf.Ticker(ticker)
    return stock.history(period="1y")

def calculate_volatility(data):
    returns = data['Close'].pct_change()
    return returns.std() * np.sqrt(252)

def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=window).mean()
    avg_loss = loss.rolling(window=window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def calculate_macd(data):
    short_ema = data['Close'].ewm(span=12, adjust=False).mean()
    long_ema = data['Close'].ewm(span=26, adjust=False).mean()
    macd = short_ema - long_ema
    signal = macd.ewm(span=9, adjust=False).mean()
    return macd, signal

def support_resistance(data, window=20):
    support = data['Low'].rolling(window=window).min()
    resistance = data['High'].rolling(window=window).max()
    return support.iloc[-1], resistance.iloc[-1]

def fetch_option_chain(symbol):
    url = f"https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    session = requests.Session()
    response = session.get(url, headers=headers)
    return response.json()

def analyze_option_chain(data):
    ce_oi_total = 0
    pe_oi_total = 0
    strikes = []
    for strike_data in data['records']['data']:
        if 'CE' in strike_data:
            ce_oi_total += strike_data['CE']['openInterest']
        if 'PE' in strike_data:
            pe_oi_total += strike_data['PE']['openInterest']
        strikes.append(strike_data['strikePrice'])
    pcr = pe_oi_total / ce_oi_total if ce_oi_total != 0 else None
    return ce_oi_total, pe_oi_total, pcr, strikes

def compute_scores(volatility, rsi, macd, signal, pcr):
    score = 0
    if volatility > 0.02: score += 2
    elif volatility > 0.015: score += 1
    if rsi < 30: score += 1
    elif rsi > 70: score -= 1
    if macd > signal: score += 1
    else: score -= 1
    if pcr > 1.2: score += 1
    elif pcr < 0.8: score += 1
    return score

def send_email_alert(csv_file, recipients):
    msg = EmailMessage()
    msg['Subject'] = 'Daily NSE Options Watchlist'
    msg['From'] = 'your_email@example.com'
    msg['To'] = ', '.join(recipients)
    msg.set_content('Attached is the daily top options watchlist.')
    with open(csv_file, 'rb') as f:
        msg.add_attachment(f.read(), maintype='application', subtype='csv', filename=csv_file)
    # Replace SMTP settings with your email provider
    with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
        smtp.login('your_email@example.com', 'your_app_password')
        smtp.send_message(msg)

# -----------------------
# Streamlit App
# -----------------------
st.set_page_config(layout="wide", page_title="Automated NSE Options Watchlist")
st.title("💹 Automated NSE Options Watchlist")

symbol_for_options = st.text_input("Index for Option Chain", "NIFTY")
run_scan = st.button("Run Daily Scan")

# Default Top 50 NSE Stocks (can extend)
top_nse_stocks = ["RELIANCE.NS","TCS.NS","HDFCBANK.NS","INFY.NS","ICICIBANK.NS",
                  "HINDUNILVR.NS","KOTAKBANK.NS","SBIN.NS","LT.NS","ITC.NS"]

if run_scan:
    all_results = []
    st.info("Starting daily scan of top NSE stocks...")
    for ticker in top_nse_stocks:
        try:
            stock_data = fetch_stock_data(ticker)
            last_close = stock_data['Close'][-1]
            volume = stock_data['Volume'][-1]
            volatility = calculate_volatility(stock_data)
            rsi_val = calculate_rsi(stock_data).iloc[-1]
            macd_val, signal_val = calculate_macd(stock_data)
            macd_val = macd_val.iloc[-1]
            signal_val = signal_val.iloc[-1]
            support, resistance = support_resistance(stock_data)

            option_data = fetch_option_chain(symbol_for_options)
            ce_oi, pe_oi, pcr, strikes = analyze_option_chain(option_data)

            score = compute_scores(volatility, rsi_val, macd_val, signal_val, pcr)

            result = {
                "Ticker": ticker,
                "Last Close": last_close,
                "Volume": volume,
                "Volatility": round(volatility,4),
                "RSI": round(rsi_val,2),
                "MACD": round(macd_val,2),
                "Signal": round(signal_val,2),
                "Support": round(support,2),
                "Resistance": round(resistance,2),
                "Call OI": ce_oi,
                "Put OI": pe_oi,
                "PCR": round(pcr,2) if pcr else None,
                "Opportunity Score": score
            }
            all_results.append(result)
            st.write(f"✅ {ticker} scanned successfully")
            time.sleep(0.5)
        except Exception as e:
            st.error(f"Error scanning {ticker}: {e}")

    df = pd.DataFrame(all_results)
    st.subheader("📊 Daily Options Watchlist")
    st.dataframe(df)

    # Highlight top 5
    top_stocks = df.sort_values(by="Opportunity Score", ascending=False).head(5)
    st.subheader("🔥 Top 5 Opportunities")
    st.dataframe(top_stocks)

    # Save CSV
    csv_file = f"Automated_Options_Watchlist_{datetime.now().strftime('%Y%m%d')}.csv"
    df.to_csv(csv_file, index=False)
    st.success(f"Watchlist saved as {csv_file}")

    # Optional: email alert
    email_alert = st.checkbox("Send Email Alert")
    if email_alert:
        recipients = st.text_input("Enter recipient emails (comma separated)", "")
        if recipients:
            send_email_alert(csv_file, [x.strip() for x in recipients.split(",")])
            st.success("Email alert sent!")