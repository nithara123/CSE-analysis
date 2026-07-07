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
def _resolve_full_symbol(short_symbol: str):
    """
    Given a short symbol as stored in your investor360 data (e.g. "SPEN"),
    figure out the full CSE symbol (e.g. "SPEN.N0000") by trying the common
    CSE share-class suffixes directly against companyInfoSummery, which
    works regardless of whether the stock traded recently.

    Order of preference:
      .N0000 - ordinary voting shares (most companies)
      .X0000 - non-voting shares (some companies only have this class)

    Returns (full_symbol_or_None, debug_info_dict).
    """
    short_symbol = short_symbol.strip().upper()

    # If it already looks like a full symbol (has a suffix), just use it as-is.
    if "." in short_symbol:
        return short_symbol, {"step": "resolve_full_symbol", "note": "already had suffix", "used": short_symbol}

    candidates = [f"{short_symbol}.N0000", f"{short_symbol}.X0000"]
    attempts = []

    for candidate in candidates:
        try:
            resp = requests.post(
                BASE_URL + "companyInfoSummery",
                data={"symbol": candidate},
                headers=HEADERS,
                timeout=15,
            )
            attempts.append({"candidate": candidate, "status_code": resp.status_code})
            if resp.status_code == 200:
                info = resp.json()
                sym_info = info.get("reqSymbolInfo") or {}
                # A valid hit will have a name and/or a lastTradedPrice populated.
                if sym_info.get("name") or sym_info.get("lastTradedPrice") is not None:
                    return candidate, {"step": "resolve_full_symbol", "attempts": attempts, "matched": candidate}
        except Exception as e:
            attempts.append({"candidate": candidate, "error": f"{type(e).__name__}: {e}"})

    return None, {"step": "resolve_full_symbol", "attempts": attempts, "matched": None}


@st.cache_data(ttl=1800, show_spinner=False)
def _resolve_stock_id(full_symbol: str):
    """
    Given a full CSE symbol (e.g. 'DIAL.N0000'), fetch companyInfoSummery
    to get the numeric id CSE uses internally for chart requests, if present.
    Falls back to the symbol string itself if no numeric id is found.

    Returns (stock_id_or_None, debug_info_dict).
    """
    debug = {"step": "companyInfoSummery", "status_code": None, "error": None, "raw": None}
    try:
        resp = requests.post(
            BASE_URL + "companyInfoSummery",
            data={"symbol": full_symbol},
            headers=HEADERS,
            timeout=15,
        )
        debug["status_code"] = resp.status_code
        resp.raise_for_status()
        info = resp.json()
        debug["raw"] = info
    except Exception as e:
        debug["error"] = f"{type(e).__name__}: {e}"
        return None, debug

    # Try common places an id might show up in the response.
    for section in ("reqSymbolInfo", "reqLogo"):
        block = info.get(section, {})
        if isinstance(block, dict) and "id" in block:
            return block["id"], debug
    return None, debug


def fetch_daily_price_history(symbol: str, period: int = 3):
    """
    Fetch and return a daily OHLC DataFrame for a CSE company.

    symbol: either a short symbol as stored in your investor360 data
            (e.g. "SPEN") or a full CSE symbol (e.g. "SPEN.N0000") — both work.
    period: CSE's internal period code for companyChartDataByStock.
            Meaning isn't publicly documented — try 1/2/3/4/5 if the
            returned range looks too short or too long for your needs.

    Returns (DataFrame, debug_trail_list). DataFrame has columns:
    Date, Open, High, Low, Close (empty DataFrame if nothing could be fetched).
    """
    trail = []

    if not symbol:
        return pd.DataFrame(), [{"step": "symbol_input", "error": "empty symbol"}]

    full_symbol, resolve_debug = _resolve_full_symbol(symbol)
    trail.append(resolve_debug)

    if not full_symbol:
        return pd.DataFrame(), trail

    stock_id, id_debug = _resolve_stock_id(full_symbol)
    trail.append(id_debug)

    payload = {"period": period}
    if stock_id is not None:
        payload["stockId"] = stock_id
    else:
        # Some deployments of this endpoint accept the symbol directly
        payload["stockId"] = full_symbol

    chart_debug = {"step": "companyChartDataByStock", "payload": payload,
                   "status_code": None, "error": None, "raw_sample": None}
    try:
        resp = requests.post(
            BASE_URL + "companyChartDataByStock",
            data=payload,
            headers=HEADERS,
            timeout=15,
        )
        chart_debug["status_code"] = resp.status_code
        resp.raise_for_status()
        raw = resp.json()
        chart_debug["raw_sample"] = str(raw)[:500]
    except Exception as e:
        chart_debug["error"] = f"{type(e).__name__}: {e}"
        trail.append(chart_debug)
        return pd.DataFrame(), trail

    trail.append(chart_debug)

    # CSE's response shape has varied in the wild — handle both:
    #   {"chartData": [...]}                     (seen in practice)
    #   {"reqTradeSummery": {"chartData": [...]}} (seen in some docs)
    if isinstance(raw, dict) and "chartData" in raw:
        chart_points = raw.get("chartData", [])
    else:
        chart_points = (raw.get("reqTradeSummery") or {}).get("chartData", [])

    if not chart_points:
        return pd.DataFrame(), trail

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

    return daily, trail


def render_price_movement_section(symbol: str, display_name: str = ""):
    """
    Streamlit component: renders a candlestick chart of daily price
    movements for the given CSE company. `symbol` can be either a short
    symbol (e.g. "SPEN") or a full CSE symbol (e.g. "SPEN.N0000") — the
    correct share class (.N0000 / .X0000) is resolved automatically.

    Fetches a fixed ~1-year window from CSE once (period=6, confirmed via
    testing to return ~363 calendar days), then lets the user slide through
    1-6 months of that data client-side — avoiding any dependence on CSE's
    undocumented period codes for fine-grained ranges.

    Call this above your financials section for the selected company.
    """
    st.markdown("### Price Movement")

    if not symbol:
        st.info("No ticker symbol available for this company.")
        return

    with st.spinner(f"Fetching price history for {symbol}..."):
        full_df, trail = fetch_daily_price_history(symbol, period=6)

    if full_df.empty:
        st.warning(
            f"Couldn't fetch price movement data for **{symbol}** right now. "
            "The CSE data endpoint may be temporarily unavailable, or this "
            "symbol couldn't be matched to a CSE share class (.N0000/.X0000)."
        )
        with st.expander("Debug details (send this to Claude if you're stuck)"):
            st.json(trail)
        return

    months_back = st.slider(
        "Months to show", min_value=1, max_value=6, value=3, step=1,
        key=f"months_{symbol}",
    )
    cutoff = (pd.Timestamp(full_df["Date"].max()) - pd.DateOffset(months=months_back)).date()
    df = full_df[full_df["Date"] >= cutoff].reset_index(drop=True)

    if df.empty:
        df = full_df

    latest = df.iloc[-1]
    prev = df.iloc[-2] if len(df) > 1 else latest
    change = latest["Close"] - prev["Close"]
    pct = (change / prev["Close"] * 100) if prev["Close"] else 0

    first_date = df["Date"].min()
    last_date = df["Date"].max()
    date_range_label = f"{first_date.strftime('%d %b')} – {last_date.strftime('%d %b %Y')}"
    change_color = "#16a34a" if change >= 0 else "#dc2626"
    change_arrow = "▲" if change >= 0 else "▼"

    def _small_metric(label, value, sub=None, sub_color="#5a7199"):
        sub_html = f'<div style="font-size:0.72rem;color:{sub_color};margin-top:2px;">{sub}</div>' if sub else ""
        st.markdown(f"""
        <div style="background:white;padding:10px;border-radius:10px;
                    border:1px solid #e0e7ef;text-align:center;height:68px;">
            <div style="font-size:0.65rem;color:#5a7199;font-weight:600;">{label}</div>
            <div style="font-size:0.95rem;font-weight:700;color:#0B1D51;white-space:nowrap;">{value}</div>
            {sub_html}
        </div>
        """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        _small_metric("Last Close", f"{latest['Close']:.2f}",
                       f"{change_arrow} {pct:.2f}%", change_color)
    with c2:
        _small_metric("Day High", f"{latest['High']:.2f}")
    with c3:
        _small_metric("Day Low", f"{latest['Low']:.2f}")
    with c4:
        _small_metric("Range", date_range_label, f"{len(df)} days")

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
