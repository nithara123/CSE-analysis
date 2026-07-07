"""
Daily Price Movement Tracker
----------------------------
A Streamlit app that pulls historical daily price data for any publicly
traded company (via its ticker symbol) and visualizes day-to-day price
movements, % change, and volatility.

Run with:
    streamlit run price_movement_app.py

Requires:
    pip install streamlit yfinance pandas plotly
"""

import streamlit as st
import yfinance as yf
import pandas as pd
import plotly.graph_objects as go
from datetime import date, timedelta

st.set_page_config(page_title="Daily Price Movement Tracker", layout="wide")

st.title("📈 Daily Price Movement Tracker")
st.caption("Track day-to-day price movements for any listed company.")

# ---------------------------
# Sidebar controls
# ---------------------------
with st.sidebar:
    st.header("Settings")

    ticker_input = st.text_input(
        "Company ticker symbol",
        value="AAPL",
        help="e.g. AAPL (Apple), MSFT (Microsoft), TSLA (Tesla), GOOGL (Alphabet)",
    ).strip().upper()

    default_start = date.today() - timedelta(days=180)
    start_date = st.date_input("Start date", value=default_start)
    end_date = st.date_input("End date", value=date.today())

    interval = st.selectbox(
        "Interval",
        options=["1d", "1wk", "1mo"],
        index=0,
        help="Granularity of price data",
    )

    show_ma = st.checkbox("Show moving averages (20/50 day)", value=True)

    fetch_button = st.button("Fetch data", type="primary")


@st.cache_data(ttl=3600, show_spinner=False)
def load_price_data(ticker: str, start: date, end: date, interval: str) -> pd.DataFrame:
    """Download historical price data for a ticker using yfinance."""
    data = yf.download(
        ticker,
        start=start,
        end=end + timedelta(days=1),  # include end date
        interval=interval,
        progress=False,
    )
    if data.empty:
        return data

    # Flatten multi-index columns if present (happens with some yfinance versions)
    if isinstance(data.columns, pd.MultiIndex):
        data.columns = data.columns.get_level_values(0)

    data = data.reset_index()
    data["Daily Change"] = data["Close"].diff()
    data["Daily % Change"] = data["Close"].pct_change() * 100
    if show_ma:
        data["MA20"] = data["Close"].rolling(20).mean()
        data["MA50"] = data["Close"].rolling(50).mean()
    return data


def get_company_name(ticker: str) -> str:
    try:
        info = yf.Ticker(ticker).info
        return info.get("longName") or info.get("shortName") or ticker
    except Exception:
        return ticker


# ---------------------------
# Main content
# ---------------------------
if ticker_input:
    with st.spinner(f"Fetching data for {ticker_input}..."):
        df = load_price_data(ticker_input, start_date, end_date, interval)

    if df.empty:
        st.error(
            f"No data found for '{ticker_input}'. Check the ticker symbol and date range."
        )
    else:
        company_name = get_company_name(ticker_input)
        st.subheader(f"{company_name} ({ticker_input})")

        latest = df.iloc[-1]
        prev = df.iloc[-2] if len(df) > 1 else latest

        col1, col2, col3, col4 = st.columns(4)
        col1.metric(
            "Latest Close",
            f"${latest['Close']:.2f}",
            f"{latest['Daily % Change']:.2f}%" if pd.notna(latest["Daily % Change"]) else None,
        )
        col2.metric("Day High", f"${latest['High']:.2f}")
        col3.metric("Day Low", f"${latest['Low']:.2f}")
        col4.metric("Volume", f"{int(latest['Volume']):,}")

        # ---------------------------
        # Price chart
        # ---------------------------
        fig = go.Figure()
        fig.add_trace(
            go.Candlestick(
                x=df["Date"],
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                name="Price",
            )
        )
        if show_ma and "MA20" in df.columns:
            fig.add_trace(
                go.Scatter(x=df["Date"], y=df["MA20"], name="MA20", line=dict(width=1))
            )
            fig.add_trace(
                go.Scatter(x=df["Date"], y=df["MA50"], name="MA50", line=dict(width=1))
            )
        fig.update_layout(
            xaxis_title="Date",
            yaxis_title="Price (USD)",
            xaxis_rangeslider_visible=False,
            height=500,
            margin=dict(l=10, r=10, t=30, b=10),
        )
        st.plotly_chart(fig, use_container_width=True)

        # ---------------------------
        # Daily % change bar chart
        # ---------------------------
        st.subheader("Daily % Change")
        change_fig = go.Figure()
        colors = ["#2ecc71" if v >= 0 else "#e74c3c" for v in df["Daily % Change"].fillna(0)]
        change_fig.add_trace(
            go.Bar(x=df["Date"], y=df["Daily % Change"], marker_color=colors)
        )
        change_fig.update_layout(
            xaxis_title="Date",
            yaxis_title="% Change",
            height=300,
            margin=dict(l=10, r=10, t=10, b=10),
        )
        st.plotly_chart(change_fig, use_container_width=True)

        # ---------------------------
        # Data table + download
        # ---------------------------
        st.subheader("Raw Data")
        display_cols = ["Date", "Open", "High", "Low", "Close", "Volume", "Daily Change", "Daily % Change"]
        st.dataframe(
            df[display_cols].sort_values("Date", ascending=False),
            use_container_width=True,
            hide_index=True,
        )

        csv = df[display_cols].to_csv(index=False).encode("utf-8")
        st.download_button(
            "Download data as CSV",
            data=csv,
            file_name=f"{ticker_input}_price_movements.csv",
            mime="text/csv",
        )
else:
    st.info("Enter a ticker symbol in the sidebar to get started.")
