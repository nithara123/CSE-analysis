"""
cse_price_chart.py
-------------------
Fetches and renders daily price movement (candlestick) charts for
Colombo Stock Exchange (CSE) listed companies, using CSE's public
(unofficial, reverse-engineered) web API — the same one that powers
charts on cse.lk.

Drop this file next to your Investor 360 app.py and import it:

    from cse_price_chart import render_price_movement_section

Then call it inside your per-company expander, above the financials:

    render_price_movement_section(fd.get("symbol"), company_name)

NOTE: This relies on an UNOFFICIAL API (no published docs from CSE).
Endpoints/field names may change without notice. If it breaks, the
`st.error` messages below will tell you what failed.
"""

import requests
import pandas as pd
import streamlit as st
import plotly.graph_objects as go
from datetime import datetime

BASE_URL = "https://www.cse.lk/api/"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.cse.lk/",
}


@st.cache_data(ttl=1800, show_spinner=False)
def _fetch_symbol_map() -> dict:
    """
    Build a map of {short_symbol: full_cse_symbol} e.g. {"DIAL": "DIAL.N0000"}
    by pulling CSE's full daily share price list once and matching on the
    prefix before the first dot.
    """
    try:
        resp = requests.post(BASE_URL + "todaySharePrice", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        rows = resp.json()
    except Exception as e:
        return {}

    mapping = {}
    if isinstance(rows, list):
        for row in rows:
            full_symbol = row.get("symbol")  # e.g. "DIAL.N0000"
            if full_symbol and "." in full_symbol:
                short = full_symbol.split(".")[0]
                mapping[short] = full_symbol
    return mapping


@st.cache_data(ttl=1800, show_spinner=False)
def _resolve_stock_id(full_symbol: str):
    """
    Given a full CSE symbol (e.g. 'DIAL.N0000'), fetch companyInfoSummery
    to get the numeric id CSE uses internally for chart requests, if present.
    Falls back to the symbol string itself if no numeric id is found.
    """
    try:
        resp = requests.post(
            BASE_URL + "companyInfoSummery",
            data={"symbol": full_symbol},
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        info = resp.json()
    except Exception:
        return None

    # Try common places an id might show up in the response.
    for section in ("reqSymbolInfo", "reqLogo"):
        block = info.get(section, {})
        if isinstance(block, dict) and "id" in block:
            return block["id"]
    return None


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_daily_price_history(short_symbol: str, period: int = 3) -> pd.DataFrame:
    """
    Fetch and return a daily OHLC DataFrame for a CSE company.

    short_symbol: the short ticker as used in your investor360 data (e.g. "DIAL")
    period: CSE's internal period code for companyChartDataByStock.
            Meaning isn't publicly documented — try 1/2/3/4/5 if the
            returned range looks too short or too long for your needs.

    Returns a DataFrame with columns: Date, Open, High, Low, Close
    (empty DataFrame if nothing could be fetched).
    """
    symbol_map = _fetch_symbol_map()
    full_symbol = symbol_map.get(short_symbol.upper())

    if not full_symbol:
        return pd.DataFrame()

    stock_id = _resolve_stock_id(full_symbol)

    payload = {"period": period}
    if stock_id is not None:
        payload["stockId"] = stock_id
    else:
        # Some deployments of this endpoint accept the symbol directly
        payload["stockId"] = full_symbol

    try:
        resp = requests.post(
            BASE_URL + "companyChartDataByStock",
            data=payload,
            headers=HEADERS,
            timeout=15,
        )
        resp.raise_for_status()
        raw = resp.json()
    except Exception:
        return pd.DataFrame()

    chart_points = (raw.get("reqTradeSummery") or {}).get("chartData", [])
    if not chart_points:
        return pd.DataFrame()

    df = pd.DataFrame(chart_points)
    # Expected fields: h (high), l (low), o (open, can be None), p (price/close), t (epoch ms)
    if "t" not in df.columns:
        return pd.DataFrame()

    df["Date"] = pd.to_datetime(df["t"], unit="ms").dt.date
    df = df.rename(columns={"h": "High", "l": "Low", "o": "Open", "p": "Close"})

    for col in ["High", "Low", "Open", "Close"]:
        if col not in df.columns:
            df[col] = None

    # Aggregate to one row per calendar day in case of multiple intraday points
    daily = df.groupby("Date").agg(
        Open=("Open", lambda s: s.dropna().iloc[0] if s.dropna().any() else None),
        High=("High", "max"),
        Low=("Low", "min"),
        Close=("Close", "last"),
    ).reset_index()

    # Fill missing Open with previous day's Close where possible
    daily["Open"] = daily["Open"].fillna(daily["Close"].shift(1))
    daily = daily.sort_values("Date")

    return daily


def render_price_movement_section(short_symbol: str, display_name: str = ""):
    """
    Streamlit component: renders a candlestick chart of daily price
    movements for the given CSE short symbol (e.g. "DIAL").
    Call this above your financials section for the selected company.
    """
    st.markdown("### Price Movement")

    if not short_symbol:
        st.info("No ticker symbol available for this company.")
        return

    with st.spinner(f"Fetching price history for {short_symbol}..."):
        df = fetch_daily_price_history(short_symbol)

    if df.empty:
        st.warning(
            f"Couldn't fetch price movement data for **{short_symbol}** right now. "
            "The CSE data endpoint may be temporarily unavailable, or this symbol "
            "doesn't match CSE's naming (e.g. it may need a suffix like `.N0000`)."
        )
        return

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    change = latest["Close"] - prev["Close"]
    pct = (change / prev["Close"] * 100) if prev["Close"] else 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Last Close", f"{latest['Close']:.2f}", f"{pct:.2f}%")
    c2.metric("Day High", f"{latest['High']:.2f}")
    c3.metric("Day Low", f"{latest['Low']:.2f}")
    c4.metric("Data Points", f"{len(df)} days")

    fig = go.Figure(
        go.Candlestick(
            x=df["Date"],
            open=df["Open"],
            high=df["High"],
            low=df["Low"],
            close=df["Close"],
            increasing_line_color="#16a34a",
            decreasing_line_color="#dc2626",
        )
    )
    fig.update_layout(
        title=dict(text=f"{display_name or short_symbol} — Daily Price Movement",
                    font=dict(color="#0B1D51", size=13), x=0),
        xaxis_rangeslider_visible=False,
        paper_bgcolor="#ffffff", plot_bgcolor="#F8F9FB",
        font=dict(color="#5a7199"),
        xaxis=dict(gridcolor="#e5eaf2"), yaxis=dict(gridcolor="#e5eaf2", title="Price (LKR)"),
        margin=dict(l=10, r=10, t=40, b=10), height=380,
    )
    st.plotly_chart(fig, use_container_width=True)
