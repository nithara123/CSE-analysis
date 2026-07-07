"""
news_intelligence.py
Market Intelligence module for Investor 360.

Pulls headlines from free public RSS feeds (Sri Lankan business press + major
international outlets), classifies them by CSE sector, tags mentioned listed
companies, scores a rough sentiment, and renders an interactive Streamlit page.
Also includes a Macro & Rates dashboard (inflation, interest rates, GDP growth,
unemployment, exchange rates) sourced from the free World Bank Open Data API,
with a world map, country comparison, and Sri Lanka historical trends.

Drop this file next to app.py and cse_price_chart.py, then:

    from news_intelligence import render_market_intelligence
    ...
    elif page == "Market Intelligence":
        render_market_intelligence(companies)

Requires: feedparser, requests, plotly  ->  pip install feedparser requests plotly
"""

import re
import time
from datetime import datetime, timedelta

import feedparser
import requests
import streamlit as st
import plotly.graph_objects as go

# ── RSS SOURCES ───────────────────────────────────────────────────────────────
# Every feed below is a free, publicly documented RSS endpoint (no API key,
# no scraping). If a feed ever goes down it is simply skipped — the page
# keeps working with whatever sources respond.
SRI_LANKA_FEEDS = {
    "Daily FT":              "https://www.ft.lk/rss",
    "EconomyNext":           "https://economynext.com/feed",
    "Lanka Business Online": "https://www.lankabusinessonline.com/feed",
}

GLOBAL_FEEDS = {
    "BBC Business": "https://feeds.bbci.co.uk/news/business/rss.xml",
    "Al Jazeera":   "https://www.aljazeera.com/xml/rss/all.xml",
}

# ── SECTOR KEYWORD MAP ───────────────────────────────────────────────────────
# Maps a CSE-relevant sector label to a list of keywords/company names that
# indicate an article belongs to it. Matching is case-insensitive substring
# matching, so keep entries lower-case.
SECTOR_KEYWORDS = {
    "Banking": ["bank", "commercial bank", "sampath", "hnb", "hatton national",
                "dfcc", "ndb", "boc", "people's bank", "seylan", "pan asia",
                "central bank", "cbsl", "monetary policy", "interest rate"],
    "Finance": ["finance company", "leasing", "lending", "microfinance",
                "lofc", "vallibel finance", "central finance"],
    "Insurance": ["insurance", "insurer", "ceylinco", "sri lanka insurance",
                  "life insurance", "general insurance"],
    "Healthcare": ["hospital", "medical", "pharmaceutical", "healthcare",
                   "asiri", "nawaloka", "durdans", "lanka hospitals"],
    "Hotels & Tourism": ["hotel", "tourism", "tourist arrivals", "resort",
                         "aitken spence", "john keells hotels", "leisure sector"],
    "Manufacturing": ["manufacturing", "factory", "industrial", "cement",
                      "tokyo cement", "steel", "packaging"],
    "Diversified": ["john keells holdings", "hayleys", "carson cumberbatch",
                    "vallibel one", "diversified conglomerate"],
    "Power & Energy": ["power plant", "electricity", "ceb", "energy sector",
                       "renewable energy", "solar power", "wind power",
                       "fuel prices", "petroleum", "ceypetco", "lp gas"],
    "Telecommunications": ["telecom", "dialog", "slt", "mobitel", "sri lanka telecom",
                           "mobile network", "broadband"],
    "Food & Beverage": ["food and beverage", "beverage", "dairy", "milk powder",
                        "nestle lanka", "cargills", "ceylon cold stores"],
    "Plantations": ["tea", "rubber", "coconut", "plantation", "export agriculture",
                    "estate", "smallholder"],
    "Construction": ["construction", "real estate", "property developer",
                     "housing", "cement demand"],
    "Transportation": ["shipping", "freight", "logistics", "port", "colombo port",
                       "container", "airline", "srilankan airlines", "aviation"],
}

MACRO_KEYWORDS = [
    "tariff", "oil price", "gold price", "inflation", "interest rate",
    "federal reserve", "central bank", "shipping disruption", "freight cost",
    "china economy", "india trade", "middle east", "exchange rate",
    "commodity price", "imf", "trade deal", "recession", "gdp growth",
]

HIGH_IMPACT_KEYWORDS = [
    "budget", "central bank", "interest rate", "monetary policy", "tax",
    "tariff", "exchange rate", "imf", "debt restructuring", "sovereign rating",
]

POSITIVE_WORDS = [
    "growth", "surge", "rally", "profit", "gain", "recovery", "boost",
    "expansion", "record high", "upgrade", "strong", "rebound", "improve",
    "beat expectations", "rise", "increase", "positive",
]
NEGATIVE_WORDS = [
    "decline", "crisis", "crash", "loss", "downgrade", "recession", "default",
    "shortage", "slump", "plunge", "fall", "concern", "risk", "weak",
    "disruption", "warning", "cut", "fear", "tension", "conflict",
]

TIME_WINDOWS = {
    "Last 24 Hours": timedelta(hours=24),
    "Last 7 Days":   timedelta(days=7),
    "Last 30 Days":  timedelta(days=30),
    "All Available":  None,
}

# ── MACRO DATA CONFIG (World Bank Open Data — free, no API key) ─────────────
# Sri Lanka plus its key trading/investment partners and the world's major
# economies, so the world map has good coverage without hammering the API.
MACRO_COUNTRIES = {
    "Sri Lanka": "LKA", "India": "IND", "China": "CHN", "United States": "USA",
    "United Kingdom": "GBR", "Japan": "JPN", "Singapore": "SGP", "Germany": "DEU",
    "France": "FRA", "Italy": "ITA", "Netherlands": "NLD", "Switzerland": "CHE",
    "United Arab Emirates": "ARE", "Saudi Arabia": "SAU", "Qatar": "QAT",
    "South Korea": "KOR", "Australia": "AUS", "Canada": "CAN", "Brazil": "BRA",
    "Russia": "RUS", "South Africa": "ZAF", "Turkey": "TUR", "Egypt": "EGY",
    "Nigeria": "NGA", "Kenya": "KEN", "Malaysia": "MYS", "Indonesia": "IDN",
    "Thailand": "THA", "Vietnam": "VNM", "Bangladesh": "BGD", "Pakistan": "PAK",
    "Nepal": "NPL", "Maldives": "MDV", "Philippines": "PHL", "Hong Kong": "HKG",
    "Mexico": "MEX", "Argentina": "ARG", "New Zealand": "NZL",
}

# label -> (World Bank indicator code, unit suffix, whether "higher" is bad)
# higher_is_bad: True = red at high values, False = green at high values,
# None = neutral (context-dependent, no good/bad color coding)
MACRO_INDICATORS = {
    "Inflation Rate (CPI, % YoY)":     {"code": "FP.CPI.TOTL.ZG",  "suffix": "%", "higher_is_bad": True},
    "Lending Interest Rate (%)":       {"code": "FR.INR.LEND",     "suffix": "%", "higher_is_bad": None},
    "Real Interest Rate (%)":          {"code": "FR.INR.RINR",     "suffix": "%", "higher_is_bad": None},
    "GDP Growth (Annual %)":           {"code": "NY.GDP.MKTP.KD.ZG", "suffix": "%", "higher_is_bad": False},
    "Unemployment Rate (%)":           {"code": "SL.UEM.TOTL.ZS",  "suffix": "%", "higher_is_bad": True},
    "Exchange Rate (LCU per US$)":     {"code": "PA.NUS.FCRF",     "suffix": "",  "higher_is_bad": None},
}

DEFAULT_COMPARE_COUNTRIES = [
    "Sri Lanka", "United States", "India", "China", "United Kingdom", "Japan", "Singapore",
]


# ── FETCHING ──────────────────────────────────────────────────────────────────
@st.cache_data(ttl=900, show_spinner=False)
def fetch_feed(source_name, url):
    """Fetch and parse a single RSS feed. Returns a list of normalized dicts.
    Any failure returns an empty list rather than raising, so one dead feed
    never breaks the page."""
    try:
        parsed = feedparser.parse(url)
        items = []
        for entry in parsed.entries[:25]:
            published_struct = entry.get("published_parsed") or entry.get("updated_parsed")
            if published_struct:
                published_dt = datetime.fromtimestamp(time.mktime(published_struct))
            else:
                published_dt = None
            summary = entry.get("summary", "") or entry.get("description", "")
            summary = re.sub("<[^<]+?>", "", summary).strip()  # strip HTML tags
            items.append({
                "title": entry.get("title", "Untitled"),
                "link": entry.get("link", ""),
                "summary": summary[:280],
                "published": published_dt,
                "source": source_name,
            })
        return items
    except Exception:
        return []


@st.cache_data(ttl=900, show_spinner=False)
def fetch_region(region_feeds_tuple):
    """region_feeds_tuple: tuple of (source_name, url) pairs (hashable for caching)."""
    all_items = []
    for source_name, url in region_feeds_tuple:
        all_items.extend(fetch_feed(source_name, url))
    all_items.sort(key=lambda x: x["published"] or datetime.min, reverse=True)
    return all_items


# ── MACRO DATA FETCHING (World Bank Open Data API) ───────────────────────────
@st.cache_data(ttl=86400, show_spinner=False)
def fetch_worldbank_latest(indicator_code, iso3_codes):
    """Fetch the latest available value of one indicator for a batch of countries
    in a single request. iso3_codes must be a tuple (hashable, for caching).
    Returns {iso3: {"value":.., "year":.., "country":..}}. Never raises —
    a failed/unreachable request just returns an empty dict."""
    codes_str = ";".join(iso3_codes)
    url = (f"https://api.worldbank.org/v2/country/{codes_str}/indicator/"
           f"{indicator_code}?format=json&per_page=300&mrnev=1")
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
            return {}
        out = {}
        for row in payload[1]:
            iso3 = row.get("countryiso3code")
            val = row.get("value")
            if iso3 and val is not None:
                out[iso3] = {
                    "value": val,
                    "year": row.get("date"),
                    "country": (row.get("country") or {}).get("value", iso3),
                }
        return out
    except Exception:
        return {}


@st.cache_data(ttl=86400, show_spinner=False)
def fetch_worldbank_series(iso3_code, indicator_code, start_year=2012, end_year=None):
    """Fetch a multi-year time series for one country/indicator. Returns
    {year:int -> value}, skipping years with no reported data."""
    if end_year is None:
        end_year = datetime.now().year
    url = (f"https://api.worldbank.org/v2/country/{iso3_code}/indicator/"
           f"{indicator_code}?format=json&date={start_year}:{end_year}&per_page=100")
    try:
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
            return {}
        series = {}
        for row in payload[1]:
            val = row.get("value")
            yr = row.get("date")
            if val is not None and yr:
                series[int(yr)] = val
        return series
    except Exception:
        return {}


def fmt_macro(val, suffix="", dec=2):
    if val is None:
        return "N/A"
    try:
        return f"{val:,.{dec}f}{suffix}"
    except Exception:
        return "N/A"


def macro_colorscale(higher_is_bad):
    """Green/red direction depends on whether a high value is good or bad news."""
    if higher_is_bad is True:
        return "RdYlGn_r"   # low = green, high = red
    elif higher_is_bad is False:
        return "RdYlGn"     # low = red, high = green
    return "Blues"          # neutral / context-dependent metric


def macro_line_chart(series_dict, title, y_label):
    """Self-contained line chart for the macro dashboard (mirrors app.py's
    line_chart helper so this module doesn't need to import from app.py)."""
    colors = ["#0B1D51", "#2563eb", "#16a34a", "#d97706", "#9333ea"]
    fig = go.Figure()
    for i, (label, series) in enumerate(series_dict.items()):
        xs = sorted(series.keys())
        fig.add_trace(go.Scatter(
            x=xs, y=[series[x] for x in xs], mode="lines+markers", name=label,
            line=dict(color=colors[i % len(colors)], width=2.5), marker=dict(size=6)))
    fig.update_layout(
        title=dict(text=title, font=dict(color="#0B1D51", size=13), x=0),
        paper_bgcolor="#ffffff", plot_bgcolor="#F8F9FB", font=dict(color="#5a7199"),
        xaxis=dict(gridcolor="#e5eaf2"), yaxis=dict(gridcolor="#e5eaf2", title=y_label),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10, r=10, t=40, b=10), height=280)
    return fig


# ── CLASSIFICATION HELPERS ───────────────────────────────────────────────────
def detect_sectors(text):
    text_l = text.lower()
    hits = [sector for sector, kws in SECTOR_KEYWORDS.items() if any(kw in text_l for kw in kws)]
    return hits


def detect_macro_topics(text):
    text_l = text.lower()
    return [kw.title() for kw in MACRO_KEYWORDS if kw in text_l]


def detect_companies(text, companies_dict):
    text_l = text.lower()
    matches = []
    for name in companies_dict.keys():
        # match on the first significant word(s) of the company name to avoid
        # requiring an exact full-name mention (e.g. "Asiri" inside "Asiri Surgical Hospital PLC")
        short = name.split(" PLC")[0].split(",")[0]
        if short.lower() in text_l or name.lower() in text_l:
            matches.append(name)
    return matches[:5]


def score_sentiment(text):
    text_l = text.lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in text_l)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text_l)
    if pos > neg:
        return "Positive", "🟢", "#16a34a"
    elif neg > pos:
        return "Negative", "🔴", "#dc2626"
    return "Neutral", "🟡", "#d97706"


def score_importance(text):
    text_l = text.lower()
    hits = sum(1 for kw in HIGH_IMPACT_KEYWORDS if kw in text_l)
    if hits >= 2:
        return 5, "High"
    elif hits == 1:
        return 4, "Medium"
    return 3, "Low"


def time_ago(dt):
    if dt is None:
        return "Unknown time"
    delta = datetime.now() - dt
    if delta.days > 0:
        return f"{delta.days}d ago"
    hours = delta.seconds // 3600
    if hours > 0:
        return f"{hours}h ago"
    minutes = (delta.seconds % 3600) // 60
    return f"{minutes}m ago"


# ── CARD RENDERING ────────────────────────────────────────────────────────────
def render_news_card(item, companies_dict):
    full_text = f"{item['title']} {item['summary']}"
    sectors = detect_sectors(full_text)
    macro = detect_macro_topics(full_text)
    tagged_companies = detect_companies(full_text, companies_dict)
    sentiment_label, sentiment_icon, sentiment_color = score_sentiment(full_text)
    stars, importance_label = score_importance(full_text)

    tag_html = ""
    for s in sectors[:4]:
        tag_html += f'<span style="background:#e0e9ff;color:#1a3a85;font-size:0.68rem;font-weight:600;padding:2px 9px;border-radius:12px;margin-right:5px;">{s}</span>'
    for m in macro[:3]:
        tag_html += f'<span style="background:#fef3c7;color:#92400e;font-size:0.68rem;font-weight:600;padding:2px 9px;border-radius:12px;margin-right:5px;">🌍 {m}</span>'

    company_html = ""
    if tagged_companies:
        chips = "".join(
            f'<span style="background:#dcfce7;color:#166534;font-size:0.68rem;font-weight:600;padding:2px 9px;border-radius:12px;margin-right:5px;">{c}</span>'
            for c in tagged_companies
        )
        company_html = f'<div style="margin-top:6px;">{chips}</div>'

    star_html = "⭐" * stars + "☆" * (5 - stars)

    st.markdown(f"""
    <div style="background:#ffffff;border:1px solid #e0e7ef;border-radius:12px;
                padding:16px 18px;margin-bottom:12px;box-shadow:0 1px 6px rgba(0,0,0,0.05);">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div style="font-weight:700;color:#0B1D51;font-size:0.95rem;flex:1;">
                <a href="{item['link']}" target="_blank" style="color:#0B1D51;text-decoration:none;">{item['title']}</a>
            </div>
            <div style="font-size:0.72rem;color:{sentiment_color};font-weight:700;white-space:nowrap;margin-left:10px;">
                {sentiment_icon} {sentiment_label}
            </div>
        </div>
        <div style="font-size:0.75rem;color:#94a3b8;margin-top:4px;">
            {item['source']} &nbsp;•&nbsp; {time_ago(item['published'])} &nbsp;•&nbsp;
            <span title="News importance">{star_html}</span>
        </div>
        <div style="font-size:0.83rem;color:#5a7199;margin-top:8px;line-height:1.5;">
            {item['summary'] if item['summary'] else 'No summary available.'}
        </div>
        <div style="margin-top:10px;">{tag_html if tag_html else '<span style="font-size:0.72rem;color:#94a3b8;">No sector match detected</span>'}</div>
        {company_html}
    </div>
    """, unsafe_allow_html=True)


# ── MACRO DASHBOARD ───────────────────────────────────────────────────────────
def render_macro_dashboard():
    """Interest rates, inflation, GDP growth, unemployment and FX — sourced live
    from the World Bank Open Data API. Free, no API key, updates daily via cache."""

    # ── Sri Lanka snapshot row ────────────────────────────────────────────────
    st.markdown("Sri Lanka Snapshot")
    snap_cols = st.columns(len(MACRO_INDICATORS))
    for col, (label, meta) in zip(snap_cols, MACRO_INDICATORS.items()):
        sl_map = fetch_worldbank_latest(meta["code"], ("LKA",))
        sl_info = sl_map.get("LKA", {})
        sl_val, sl_year = sl_info.get("value"), sl_info.get("year", "—")
        with col:
            st.markdown(f"""
            <div style="background:#ffffff;border:1px solid #e0e7ef;border-radius:10px;
                        padding:12px 8px;text-align:center;height:92px;">
                <div style="font-size:0.64rem;color:#5a7199;font-weight:600;line-height:1.2;">{label}</div>
                <div style="font-size:1.05rem;font-weight:800;color:#0B1D51;margin-top:6px;">
                    {fmt_macro(sl_val, meta['suffix'])}
                </div>
                <div style="font-size:0.62rem;color:#94a3b8;">as of {sl_year}</div>
            </div>""", unsafe_allow_html=True)

    st.divider()

    # ── Indicator picker + world map ──────────────────────────────────────────
    m1, m2 = st.columns([1.4, 2.6])
    with m1:
        indicator_label = st.selectbox("Indicator to map", list(MACRO_INDICATORS.keys()), key="macro_indicator")
    ind = MACRO_INDICATORS[indicator_label]

    with st.spinner("Fetching World Bank data..."):
        data_map = fetch_worldbank_latest(ind["code"], tuple(MACRO_COUNTRIES.values()))

    st.markdown(f"World Map - {indicator_label}")
    if not data_map:
        st.info("World Bank data is temporarily unreachable for this indicator. Try again shortly.")
    else:
        locs  = list(data_map.keys())
        vals  = [data_map[l]["value"] for l in locs]
        names = [f"{data_map[l]['country']} ({data_map[l]['year']})" for l in locs]
        fig_map = go.Figure(go.Choropleth(
            locations=locs, z=vals, locationmode="ISO-3", text=names,
            colorscale=macro_colorscale(ind["higher_is_bad"]),
            colorbar=dict(title=ind["suffix"] or "value", thickness=14),
            marker_line_color="#ffffff", marker_line_width=0.5,
            hovertemplate="%{text}<br>" + indicator_label + ": %{z:.2f}<extra></extra>",
        ))
        fig_map.update_layout(
            geo=dict(showframe=False, showcoastlines=True, projection_type="natural earth",
                     bgcolor="rgba(0,0,0,0)", landcolor="#eef2f7", lakecolor="#F8F9FB",
                     coastlinecolor="#c8d3e0"),
            paper_bgcolor="#ffffff", margin=dict(l=0, r=0, t=6, b=0), height=430,
        )
        st.plotly_chart(fig_map, use_container_width=True)
        st.caption(f"Latest reported value per country · Source: World Bank ({ind['code']}) · "
                   f"Countries shown: {len(locs)}/{len(MACRO_COUNTRIES)} (some may not report every indicator).")

    st.divider()

    # ── Country comparison bars ───────────────────────────────────────────────
    st.markdown(f"Country Comparison - {indicator_label}")
    compare_countries = st.multiselect(
        "Countries to compare", list(MACRO_COUNTRIES.keys()),
        default=[c for c in DEFAULT_COMPARE_COUNTRIES if c in MACRO_COUNTRIES],
        key="macro_compare",
    )
    if compare_countries:
        if data_map:
            rows = []
            for cname in compare_countries:
                iso3 = MACRO_COUNTRIES[cname]
                v = data_map.get(iso3, {}).get("value")
                if v is not None:
                    rows.append((cname, v))
            rows.sort(key=lambda r: r[1])
            if rows:
                bar_colors = ["#dc2626" if name == "Sri Lanka" else "#0B1D51" for name, _ in rows]
                fig_bar = go.Figure(go.Bar(
                    x=[r[1] for r in rows], y=[r[0] for r in rows], orientation="h",
                    marker_color=bar_colors,
                    text=[f"{r[1]:.2f}{ind['suffix']}" for r in rows],
                    textposition="outside", textfont=dict(color="#5a7199", size=10),
                ))
                fig_bar.update_layout(
                    paper_bgcolor="#ffffff", plot_bgcolor="#F8F9FB", font=dict(color="#5a7199"),
                    xaxis=dict(gridcolor="#e5eaf2", title=indicator_label), yaxis=dict(gridcolor="#e5eaf2"),
                    margin=dict(l=10, r=10, t=20, b=10), height=max(280, len(rows) * 42),
                )
                st.plotly_chart(fig_bar, use_container_width=True)
                st.caption("🇱🇰 Sri Lanka is highlighted in red for quick reference.")
            else:
                st.info("No data available for the selected countries and indicator.")
    else:
        st.caption("Pick one or more countries above to compare against Sri Lanka.")

    st.divider()

    # ── Sri Lanka historical trend ────────────────────────────────────────────
    st.markdown("Sri Lanka - 12-Year Trend")
    t1, t2 = st.columns(2)
    with t1:
        infl_series = fetch_worldbank_series("LKA", MACRO_INDICATORS["Inflation Rate (CPI, % YoY)"]["code"])
        if infl_series:
            st.plotly_chart(macro_line_chart({"Inflation % (YoY)": infl_series},
                             "Sri Lanka — Inflation Trend", "%"), use_container_width=True)
        else:
            st.info("Inflation trend data unavailable.")
    with t2:
        rate_series = fetch_worldbank_series("LKA", MACRO_INDICATORS["Lending Interest Rate (%)"]["code"])
        if rate_series:
            st.plotly_chart(macro_line_chart({"Lending Rate %": rate_series},
                             "Sri Lanka — Lending Interest Rate", "%"), use_container_width=True)
        else:
            st.info("Interest rate trend data unavailable.")

    st.info(
        "💡 **Using this for exports:** if a covered company sells mainly into a specific market "
        "(e.g. the US or an EU country), watch that country's inflation and interest-rate trend above — "
        "it drives demand and currency effects on Sri Lankan exports. Bilateral tariff schedules aren't "
        "available from a free public API, so for tariff-specific exposure check the Sri Lanka Export "
        "Development Board (srilankabusiness.com) or the destination country's customs authority directly."
    )


# ── MAIN PAGE ─────────────────────────────────────────────────────────────────
def render_market_intelligence(companies):
    """Main entry point — call this from app.py inside the page router."""
    st.markdown("Market Intelligence")
    st.caption("Live headlines from Sri Lankan and international sources, auto-tagged by sector, "
               "company, sentiment, and importance, plus a macro dashboard for rates, inflation, and "
               "growth. News refreshes every 15 minutes; macro data refreshes daily.")

    tab_sl, tab_global, tab_macro = st.tabs(["Local Updates", "International Updates", "Macro & Rates"])

    # ── Sri Lanka tab ─────────────────────────────────────────────────────────
    with tab_sl:
        f1, f2, f3 = st.columns([1, 1.4, 1.6])
        with f1:
            window_label = st.selectbox("Time range", list(TIME_WINDOWS.keys()), key="sl_window")
        with f2:
            sector_filter = st.multiselect("Sector", list(SECTOR_KEYWORDS.keys()), key="sl_sector")
        with f3:
            search_q = st.text_input("Search", placeholder="e.g. banking, tea, interest rate", key="sl_search")

        with st.spinner("Fetching Sri Lankan headlines..."):
            items = fetch_region(tuple(SRI_LANKA_FEEDS.items()))

        items = _apply_filters(items, window_label, sector_filter, search_q)

        st.markdown(f"**{len(items)} article(s) match your filters.**")
        if not items:
            st.info("No articles found for the selected filters, or the RSS sources are temporarily unreachable.")
        for item in items[:40]:
            render_news_card(item, companies)

    # ── Global tab ────────────────────────────────────────────────────────────
    with tab_global:
        g1, g2 = st.columns([1, 2])
        with g1:
            window_label_g = st.selectbox("Time range", list(TIME_WINDOWS.keys()), key="g_window")
        with g2:
            search_q_g = st.text_input("Search", placeholder="e.g. tariffs, oil, Fed, China", key="g_search")

        with st.spinner("Fetching global headlines..."):
            items_g = fetch_region(tuple(GLOBAL_FEEDS.items()))

        items_g = _apply_filters(items_g, window_label_g, [], search_q_g)

        st.markdown(f"**{len(items_g)} article(s) match your filters.**")
        st.caption("Global stories are shown as-is; sector/company tags only fire when the text "
                   "happens to mention a matching keyword or listed company.")
        if not items_g:
            st.info("No articles found for the selected filters, or the RSS sources are temporarily unreachable.")
        for item in items_g[:40]:
            render_news_card(item, companies)

    # ── Macro & Rates tab ─────────────────────────────────────────────────────
    with tab_macro:
        render_macro_dashboard()


def _apply_filters(items, window_label, sector_filter, search_q):
    window = TIME_WINDOWS[window_label]
    if window is not None:
        cutoff = datetime.now() - window
        items = [i for i in items if i["published"] is None or i["published"] >= cutoff]

    if sector_filter:
        filtered = []
        for i in items:
            text = f"{i['title']} {i['summary']}"
            if any(s in detect_sectors(text) for s in sector_filter):
                filtered.append(i)
        items = filtered

    if search_q:
        q = search_q.lower()
        items = [i for i in items if q in i["title"].lower() or q in i["summary"].lower()]

    return items
