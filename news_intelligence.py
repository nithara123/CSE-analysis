"""
news_intelligence.py
Market Intelligence module for Investor 360.

Pulls headlines from free public RSS feeds (Sri Lankan business press + major
international outlets), classifies them by CSE sector, tags mentioned listed
companies, scores a rough sentiment, and renders an interactive Streamlit page.

Drop this file next to app.py and cse_price_chart.py, then:

    from news_intelligence import render_market_intelligence
    ...
    elif page == "Market Intelligence":
        render_market_intelligence(companies)

Requires: feedparser  ->  pip install feedparser
"""

import re
import time
from datetime import datetime, timedelta

import feedparser
import streamlit as st

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


# ── MAIN PAGE ─────────────────────────────────────────────────────────────────
def render_market_intelligence(companies):
    """Main entry point — call this from app.py inside the page router."""
    st.markdown("Market Intelligence")
    st.caption("Live headlines from Sri Lankan and international sources")

    tab_sl, tab_global = st.tabs(["Local Updates", "International Updates"])

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
