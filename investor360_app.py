import streamlit as st
import json
import random
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Investor 360 | CSE Analytics", layout="wide", initial_sidebar_state="expanded")

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    .stApp { background-color: #F8F9FB; color: #1a1a2e; }
    section[data-testid="stSidebar"] { background-color: #0B1D51; }
    section[data-testid="stSidebar"] * { color: #d0e4ff !important; }
    header[data-testid="stHeader"] { background: transparent; }

    [data-testid="metric-container"] {
        background: #ffffff; border: 1px solid #e0e7ef;
        border-radius: 10px; padding: 16px;
        box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    }
    [data-testid="metric-container"] label {
        color: #5a7199 !important; font-size: 0.76rem;
        font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
    }
    [data-testid="metric-container"] [data-testid="metric-value"] {
        color: #0B1D51 !important; font-size: 1.2rem !important; font-weight: 700;
    }
    .quote-banner {
        background: linear-gradient(90deg, #0B1D51, #1a3a85);
        border-radius: 10px; padding: 14px 22px; margin-bottom: 20px;
        font-style: italic; color: #d0e4ff; font-size: 0.95rem;
    }
    .section-card {
        background: #ffffff; border-radius: 12px; padding: 22px;
        margin-bottom: 16px; border: 1px solid #e0e7ef;
        box-shadow: 0 1px 6px rgba(0,0,0,0.05);
    }
    .tag-good { background:#dcfce7; color:#166534; padding:2px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .tag-ok   { background:#fef9c3; color:#854d0e; padding:2px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }
    .tag-bad  { background:#fee2e2; color:#991b1b; padding:2px 10px; border-radius:20px; font-size:0.78rem; font-weight:600; }

    h1 { color:#0B1D51 !important; font-size:2rem !important; font-weight:800 !important; }
    h2 { color:#0B1D51 !important; font-size:1.4rem !important; font-weight:700 !important; }
    h3 { color:#0B1D51 !important; font-size:1.05rem !important; font-weight:600 !important; }

    .stTabs [role="tab"] { color:#5a7199; font-weight:600; font-size:0.88rem; }
    .stTabs [role="tab"][aria-selected="true"] { color:#0B1D51; border-bottom:3px solid #0B1D51; }
    .stSelectbox label, .stSlider label, .stMultiSelect label, .stRadio label {
        color:#0B1D51 !important; font-weight:600; font-size:0.84rem;
    }
    .block-container { padding-top:1.5rem; padding-bottom:2rem; }

    .company-header {
        background: linear-gradient(135deg, #0B1D51 0%, #1a3a85 100%);
        border-radius: 10px; padding: 16px 22px; margin-bottom: 16px; color: white;
    }

    /* Investor type selector */
    .investor-box {
        border: 2px solid #e0e7ef; border-radius: 12px; padding: 18px 22px;
        background: #ffffff; cursor: pointer; transition: all 0.2s;
    }
    .investor-box.active { border-color: #0B1D51; background: #f0f4ff; }
    .investor-box h4 { color: #0B1D51; margin: 0 0 6px 0; font-size: 1rem; }
    .investor-box p { color: #5a7199; font-size: 0.83rem; margin: 0; }

    /* Score display */
    .score-block {
        background: #ffffff; border-radius: 12px; padding: 20px;
        border: 1px solid #e0e7ef; text-align: center;
        box-shadow: 0 1px 6px rgba(0,0,0,0.05);
    }
    .score-num { font-size: 2.8rem; font-weight: 800; line-height: 1; }
    .score-label { font-size: 0.78rem; color: #5a7199; text-transform: uppercase;
                   letter-spacing: 0.06em; margin-top: 4px; font-weight: 600; }
    .score-verdict { font-size: 0.88rem; font-weight: 600; margin-top: 8px; }

    /* Criteria row */
    .criteria-row {
        display: flex; align-items: flex-start; gap: 12px;
        padding: 10px 0; border-bottom: 1px solid #f1f5f9;
    }
    .criteria-icon { font-size: 1rem; min-width: 22px; margin-top: 1px; }
    .criteria-name { font-weight: 600; color: #0B1D51; font-size: 0.88rem; }
    .criteria-detail { color: #5a7199; font-size: 0.82rem; margin-top: 2px; }
    .criteria-pts { font-size: 0.8rem; color: #2563eb; font-weight: 700;
                    margin-left: auto; white-space: nowrap; padding-left: 12px; }

    .footer {
        text-align:center; color:#94a3b8; font-size:0.78rem;
        padding:24px 0 8px 0; border-top:1px solid #e0e7ef; margin-top:40px;
    }
</style>
""", unsafe_allow_html=True)

# ── Load Data ─────────────────────────────────────────────────────────────────
@st.cache_data
def load_data():
    with open("investor360_data.json", "r", encoding="utf-8") as f:
        return json.load(f)

data         = load_data()
companies    = data.get("companies", {})
brokers      = data.get("brokers", [])
sectors      = data.get("sectors", {})

# ── Quotes ────────────────────────────────────────────────────────────────────
QUOTES = [
    ("Price is what you pay. Value is what you get.", "Warren Buffett"),
    ("The intelligent investor is a realist who sells to optimists and buys from pessimists.", "Benjamin Graham"),
    ("An investment in knowledge pays the best interest.", "Benjamin Franklin"),
    ("The stock market is filled with individuals who know the price of everything, but the value of nothing.", "Philip Fisher"),
    ("Risk comes from not knowing what you are doing.", "Warren Buffett"),
    ("In investing, what is comfortable is rarely profitable.", "Robert Arnott"),
    ("Time in the market beats timing the market.", "Ken Fisher"),
    ("Never invest in a business you cannot understand.", "Warren Buffett"),
    ("Know what you own, and know why you own it.", "Peter Lynch"),
    ("The market is a device for transferring money from the impatient to the patient.", "Warren Buffett"),
    ("Wide diversification is only required when investors do not understand what they are doing.", "Warren Buffett"),
    ("The best investment you can make is in yourself.", "Warren Buffett"),
]
if "quote" not in st.session_state:
    st.session_state.quote = random.choice(QUOTES)
q_text, q_author = st.session_state.quote

# ── Helpers ───────────────────────────────────────────────────────────────────
def get_series(fd, *keys):
    d = fd
    for k in keys:
        if not isinstance(d, dict): return {}
        d = d.get(k, {})
    if not isinstance(d, dict): return {}
    return {y: v for y, v in d.items() if v is not None}

def latest(s):
    if not s: return None
    return s.get(max(s.keys()))

def n_years(s, n):
    """Return values from the most recent n years."""
    if not s: return {}
    yrs = sorted(s.keys(), reverse=True)[:n]
    return {y: s[y] for y in yrs}

def all_positive(s):
    if not s: return False
    return all(v > 0 for v in s.values())

def any_positive(s):
    return any(v > 0 for v in s.values()) if s else False

def fmt(val, prefix="", suffix="", dec=2):
    if val is None: return "N/A"
    try: return f"{prefix}{val:,.{dec}f}{suffix}"
    except: return "N/A"

def fmt_large(val):
    if val is None: return "N/A"
    try:
        if abs(val) >= 1e9: return f"LKR {val/1e9:,.2f}B"
        if abs(val) >= 1e6: return f"LKR {val/1e6:,.2f}M"
        if abs(val) >= 1e3: return f"LKR {val/1e3:,.1f}K"
        return f"LKR {val:,.0f}"
    except: return "N/A"

C = ["#0B1D51","#2563eb","#16a34a","#d97706","#9333ea"]

def line_chart(series_dict, title, y_label):
    fig = go.Figure()
    for i, (label, series) in enumerate(series_dict.items()):
        xs = sorted(series.keys())
        fig.add_trace(go.Scatter(x=xs, y=[series[x] for x in xs], mode="lines+markers",
            name=label, line=dict(color=C[i%len(C)], width=2.5), marker=dict(size=6)))
    fig.update_layout(
        title=dict(text=title, font=dict(color="#0B1D51", size=13), x=0),
        paper_bgcolor="#ffffff", plot_bgcolor="#F8F9FB", font=dict(color="#5a7199"),
        xaxis=dict(gridcolor="#e5eaf2"), yaxis=dict(gridcolor="#e5eaf2", title=y_label),
        legend=dict(bgcolor="rgba(0,0,0,0)"),
        margin=dict(l=10,r=10,t=40,b=10), height=285)
    return fig

# ═══════════════════════════════════════════════════════════════════════════════
# SCORING ENGINES
# ═══════════════════════════════════════════════════════════════════════════════

def score_defensive(fd):
    """
    Defensive Investor — uses 10 years of data.
    Total: 100 points across 7 criteria.
    Returns: (total_score, criteria_list)
    Each criterion: {name, points_earned, points_max, met, detail, description}
    """
    results = []

    eps_all  = get_series(fd, "income_statement", "eps")
    div_all  = get_series(fd, "income_statement", "dividend_per_share")
    cr_all   = get_series(fd, "ratios", "current_ratio")
    pe_all   = get_series(fd, "market_metrics", "pe_ratio")
    mp_all   = get_series(fd, "market_metrics", "market_price")
    iv_all   = get_series(fd, "graham_analysis", "intrinsic_value")
    mos_all  = get_series(fd, "graham_analysis", "margin_of_safety")
    dr_all   = get_series(fd, "ratios", "debt_ratio")

    eps_10 = n_years(eps_all, 10)
    div_10 = n_years(div_all, 10)

    # 1. Earnings Consistency — 20 pts
    # All 10 years of EPS must be positive
    if len(eps_10) >= 10 and all_positive(eps_10):
        pts = 20; met = True
        detail = f"Positive EPS across all {len(eps_10)} available years."
    elif len(eps_10) >= 7 and all_positive(eps_10):
        pts = 12; met = False
        detail = f"Positive EPS across {len(eps_10)} years (need 10)."
    elif any_positive(eps_10):
        pts = 5; met = False
        neg_count = sum(1 for v in eps_10.values() if v <= 0)
        detail = f"{neg_count} year(s) with negative/zero EPS detected."
    else:
        pts = 0; met = False
        detail = "EPS data insufficient or all negative."
    results.append({"name":"Earnings Consistency (10 Years)", "pts":pts, "max":20, "met":met,
        "detail":detail, "desc":"Company must have positive EPS for all of the last 10 years."})

    # 2. Dividend History — 15 pts
    # Uninterrupted dividends for 10+ years
    paid_years = [y for y, v in div_10.items() if v and v > 0]
    if len(paid_years) >= 10:
        pts = 15; met = True
        detail = f"Dividends paid in all {len(paid_years)} available years."
    elif len(paid_years) >= 6:
        pts = 8; met = False
        detail = f"Dividends paid in {len(paid_years)}/10 years (need 10)."
    else:
        pts = 0; met = False
        detail = f"Dividends paid in only {len(paid_years)} year(s) — insufficient."
    results.append({"name":"Dividend History (10 Years)", "pts":pts, "max":15, "met":met,
        "detail":detail, "desc":"Uninterrupted dividend payments for at least 10 years."})

    # 3. Financial Health (Current Ratio) — 15 pts
    cr_v = latest(cr_all)
    if cr_v and cr_v >= 2.0:
        pts = 15; met = True
        detail = f"Current ratio = {cr_v:.2f} (above required 2.0)."
    elif cr_v and cr_v >= 1.5:
        pts = 8; met = False
        detail = f"Current ratio = {cr_v:.2f} (below required 2.0, above 1.5)."
    else:
        pts = 0; met = False
        detail = f"Current ratio = {fmt(cr_v)} (below minimum threshold of 2.0)."
    results.append({"name":"Financial Health — Current Ratio >= 2.0", "pts":pts, "max":15, "met":met,
        "detail":detail, "desc":"Current ratio of at least 2.0 to ensure strong short-term liquidity."})

    # 4. Low Debt — 10 pts
    dr_v = latest(dr_all)
    if dr_v and dr_v < 0.5:
        pts = 10; met = True
        detail = f"Debt ratio = {dr_v:.3f} (conservative leverage)."
    elif dr_v and dr_v < 0.65:
        pts = 5; met = False
        detail = f"Debt ratio = {dr_v:.3f} (moderate — above preferred 0.5)."
    else:
        pts = 0; met = False
        detail = f"Debt ratio = {fmt(dr_v)} (high leverage — above 0.65)."
    results.append({"name":"Low Debt (Debt Ratio < 0.5)", "pts":pts, "max":10, "met":met,
        "detail":detail, "desc":"Low debt-to-asset ratio to ensure financial stability."})

    # 5. Valuation — P/E Limit — 15 pts
    # Must not pay more than 20x last 12-month earnings or 25x 7-year avg
    pe_v = latest(pe_all)
    eps_7 = n_years(eps_all, 7)
    eps_7_avg = sum(eps_7.values()) / len(eps_7) if eps_7 else None
    mp_v = latest(mp_all)
    pe_7yr = (mp_v / eps_7_avg) if (mp_v and eps_7_avg and eps_7_avg > 0) else None
    pe_ok = (pe_v and 0 < pe_v <= 20) if pe_v else False
    pe7_ok = (pe_7yr and 0 < pe_7yr <= 25) if pe_7yr else False
    if pe_ok and pe7_ok:
        pts = 15; met = True
        detail = f"P/E (latest) = {fmt(pe_v)}, P/E (7yr avg EPS) = {fmt(pe_7yr)}. Both within limits."
    elif pe_ok or pe7_ok:
        pts = 8; met = False
        detail = f"P/E (latest) = {fmt(pe_v)}, P/E (7yr avg EPS) = {fmt(pe_7yr)}. One limit exceeded."
    else:
        pts = 0; met = False
        detail = f"P/E (latest) = {fmt(pe_v)}, P/E (7yr avg EPS) = {fmt(pe_7yr)}. Both limits exceeded."
    results.append({"name":"Valuation Limits (P/E <= 20 latest, <= 25 on 7yr avg)", "pts":pts, "max":15, "met":met,
        "detail":detail, "desc":"Avoid paying more than 20x last 12-month earnings or 25x 7-year average earnings."})

    # 6. Margin of Safety — 15 pts
    mos_v = latest(mos_all)
    if mos_v and mos_v >= 0.33:
        pts = 15; met = True
        detail = f"Margin of safety = {mos_v:.1%} (strong protection above 33%)."
    elif mos_v and mos_v > 0:
        pts = 7; met = False
        detail = f"Margin of safety = {mos_v:.1%} (positive but below the recommended 33%)."
    else:
        pts = 0; met = False
        detail = f"Margin of safety = {fmt(mos_v)} (zero or negative — stock may be overvalued)."
    results.append({"name":"Margin of Safety >= 33%", "pts":pts, "max":15, "met":met,
        "detail":detail, "desc":"Buy at a price significantly below intrinsic value to protect against error."})

    # 7. Company Size / Quality (proxy: book value > 0 and consistent revenue) — 10 pts
    bv_v = latest(get_series(fd, "market_metrics", "bvps"))
    rev_s = get_series(fd, "income_statement", "total_revenue")
    rev_10 = n_years(rev_s, 10)
    rev_positive = all(v > 0 for v in rev_10.values()) if rev_10 else False
    if bv_v and bv_v > 0 and rev_positive:
        pts = 10; met = True
        detail = f"Positive book value ({fmt(bv_v, 'LKR ')}) and consistent positive revenue across available years."
    elif bv_v and bv_v > 0:
        pts = 5; met = False
        detail = f"Positive book value but revenue inconsistency detected."
    else:
        pts = 0; met = False
        detail = f"Negative or zero book value detected."
    results.append({"name":"Company Quality (Positive Book Value & Revenue)", "pts":pts, "max":10, "met":met,
        "detail":detail, "desc":"Large, established company with positive book value and consistent revenue."})

    total = sum(r["pts"] for r in results)
    return total, results


def score_enterprising(fd):
    """
    Enterprising Investor — uses 5 years of data.
    Total: 100 points across 5 criteria.
    """
    results = []

    eps_all = get_series(fd, "income_statement", "eps")
    div_all = get_series(fd, "income_statement", "dividend_per_share")
    cr_all  = get_series(fd, "ratios", "current_ratio")
    pe_all  = get_series(fd, "market_metrics", "pe_ratio")
    pb_all  = get_series(fd, "market_metrics", "pb_ratio")
    ltd_all = get_series(fd, "balance_sheet", "long_term_debt")
    wc_all  = get_series(fd, "balance_sheet", "net_current_assets")
    eps_g   = get_series(fd, "growth", "eps_growth_yoy")

    eps_5 = n_years(eps_all, 5)
    div_5 = n_years(div_all, 5)
    eps_g5 = n_years(eps_g, 5)

    # 1. Financial Strength — 25 pts
    cr_v  = latest(cr_all)
    ltd_v = latest(ltd_all)
    wc_v  = latest(wc_all)
    cr_ok  = cr_v and cr_v > 1.5
    ltd_ok = (ltd_v and wc_v and wc_v > 0 and ltd_v < 1.1 * wc_v) if (ltd_v and wc_v) else None
    pts_cr  = 12 if cr_ok else (6 if cr_v and cr_v >= 1.0 else 0)
    pts_ltd = 13 if ltd_ok else (6 if ltd_ok is None else 0)
    pts = pts_cr + pts_ltd
    met = cr_ok and bool(ltd_ok)
    cr_detail  = f"Current ratio = {fmt(cr_v)} ({'above' if cr_ok else 'below'} required 1.5)."
    ltd_detail = f"Long-term debt = {fmt_large(ltd_v)}, Working capital = {fmt_large(wc_v)}."
    ltd_status = "Within 110% of working capital." if ltd_ok else ("N/A — negative/zero WC." if ltd_ok is None else "Exceeds 110% of working capital.")
    results.append({"name":"Financial Strength", "pts":pts, "max":25, "met":met,
        "detail":f"{cr_detail} {ltd_detail} {ltd_status}",
        "desc":"Current ratio > 1.5 and long-term debt < 110% of working capital."})

    # 2. Earnings Stability (5 years) — 20 pts
    if len(eps_5) >= 5 and all_positive(eps_5):
        pts = 20; met = True
        detail = f"Positive EPS in all {len(eps_5)} of the last 5 years."
    elif len(eps_5) >= 3 and all_positive({y:v for y,v in eps_5.items()}):
        pts = 10; met = False
        detail = f"Positive EPS in {len(eps_5)} years but full 5-year data not available."
    elif any_positive(eps_5):
        neg = sum(1 for v in eps_5.values() if v <= 0)
        pts = 5; met = False
        detail = f"{neg} year(s) with negative/zero EPS in the last 5 years."
    else:
        pts = 0; met = False
        detail = "No positive EPS in the last 5 years."
    results.append({"name":"Earnings Stability (5 Years)", "pts":pts, "max":20, "met":met,
        "detail":detail, "desc":"Positive EPS for each of the last 5 years."})

    # 3. Dividend Record — 15 pts
    paid = [y for y, v in div_5.items() if v and v > 0]
    if len(paid) >= 5:
        pts = 15; met = True
        detail = f"Dividends paid in all {len(paid)} of the last 5 years."
    elif len(paid) >= 3:
        pts = 8; met = False
        detail = f"Dividends paid in {len(paid)}/5 years."
    elif len(paid) >= 1:
        pts = 4; met = False
        detail = f"Dividends paid in only {len(paid)} year(s) in the last 5 years."
    else:
        pts = 0; met = False
        detail = "No dividends paid in the last 5 years."
    results.append({"name":"Dividend Record (5 Years)", "pts":pts, "max":15, "met":met,
        "detail":detail, "desc":"Company should pay some level of dividends, indicating shareholder-friendly management."})

    # 4. Valuation Metrics (P/E and P/B) — 25 pts
    pe_v = latest(pe_all)
    pb_v = latest(pb_all)
    pe_ok = pe_v and 0 < pe_v <= 15
    pb_ok = pb_v and 0 < pb_v <= 1.5
    pts_pe = 13 if (pe_v and 0 < pe_v <= 10) else (9 if pe_ok else (4 if pe_v and 0 < pe_v <= 20 else 0))
    pts_pb = 12 if (pb_v and 0 < pb_v <= 1.2) else (8 if pb_ok else (3 if pb_v and 0 < pb_v <= 2.0 else 0))
    pts = pts_pe + pts_pb
    met = bool(pe_ok and pb_ok)
    detail = f"P/E = {fmt(pe_v)} (target <= 15), P/B = {fmt(pb_v)} (target <= 1.5)."
    results.append({"name":"Valuation (P/E <= 15, P/B <= 1.5)", "pts":pts, "max":25, "met":met,
        "detail":detail, "desc":"P/E ratio below 10–15 and P/B ratio below 1.2–1.5, signalling undervaluation."})

    # 5. Earnings Growth (5 years) — 15 pts
    pos_growth_years = [y for y, v in eps_g5.items() if v and v > 0]
    avg_growth = sum(eps_g5.values()) / len(eps_g5) if eps_g5 else None
    if len(pos_growth_years) >= 4 and avg_growth and avg_growth > 0:
        pts = 15; met = True
        detail = f"Positive EPS growth in {len(pos_growth_years)}/5 years. Avg growth = {avg_growth:.1%}."
    elif len(pos_growth_years) >= 3:
        pts = 8; met = False
        detail = f"Positive EPS growth in {len(pos_growth_years)}/5 years."
    elif len(pos_growth_years) >= 1:
        pts = 4; met = False
        detail = f"EPS growth positive in only {len(pos_growth_years)} year(s) over 5 years."
    else:
        pts = 0; met = False
        detail = "No positive EPS growth detected in the last 5 years."
    results.append({"name":"Earnings Growth (5 Years)", "pts":pts, "max":15, "met":met,
        "detail":detail, "desc":"Demonstrated earnings growth over the past 5 years."})

    total = sum(r["pts"] for r in results)
    return total, results


def render_score_card(score, label):
    if score >= 75:   color, verdict = "#16a34a", "Strong — Meets Criteria"
    elif score >= 50: color, verdict = "#d97706", "Moderate — Partially Meets Criteria"
    else:             color, verdict = "#dc2626", "Weak — Does Not Meet Criteria"
    st.markdown(f"""
    <div class="score-block">
        <div class="score-num" style="color:{color};">{score}</div>
        <div style="font-size:0.7rem; color:#94a3b8; margin-top:2px;">out of 100</div>
        <div class="score-label">{label}</div>
        <div class="score-verdict" style="color:{color};">{verdict}</div>
    </div>""", unsafe_allow_html=True)


def render_criteria(criteria_list):
    for c in criteria_list:
        icon = "✅" if c["met"] else "❌"
        pts_color = "#16a34a" if c["pts"] == c["max"] else ("#d97706" if c["pts"] > 0 else "#dc2626")
        st.markdown(f"""
        <div class="criteria-row">
            <div class="criteria-icon">{icon}</div>
            <div style="flex:1;">
                <div class="criteria-name">{c['name']}</div>
                <div class="criteria-detail" style="color:#64748b; font-size:0.8rem; font-style:italic; margin-top:1px;">{c['desc']}</div>
                <div class="criteria-detail">{c['detail']}</div>
            </div>
            <div class="criteria-pts" style="color:{pts_color};">{c['pts']}/{c['max']} pts</div>
        </div>""", unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## Investor 360")
    st.markdown("*Colombo Stock Exchange Analytics*")
    st.divider()
    page = st.radio("", [
        "Home", "Company Analysis", "Broker Comparison",
        "Sector Analytics", "Educational Portal",
    ], label_visibility="collapsed")
    st.divider()
    st.markdown(f"""
    <div style='font-size:0.8rem; color:#90b8e0;'>
    Companies: {data['meta']['total_companies']}<br>
    Brokers: {data['meta']['total_brokers']}<br>
    Sectors: {data['meta']['total_sectors']}<br>
    Data: {data['meta']['data_years']}
    </div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
if page == "Home":
    st.markdown(f'<div class="quote-banner">"{q_text}" &nbsp;— <strong>{q_author}</strong></div>', unsafe_allow_html=True)
    st.markdown("# Investor 360")
    st.markdown("#### A data-driven analytics platform for the Colombo Stock Exchange")
    st.divider()
    m1,m2,m3,m4 = st.columns(4)
    m1.metric("Companies Covered","186"); m2.metric("Brokers Profiled","13")
    m3.metric("Sectors Analysed","21");   m4.metric("Years of Data","2016–2025")
    st.divider()
    st.markdown("### What This Platform Offers")
    c1,c2,c3 = st.columns(3)
    for col,title,desc in [
        (c1,"Company Analysis","Select up to 3 CSE companies. Choose Defensive (10-year) or Enterprising (5-year) investor mode. Get full financial dashboards, scoring out of 100, and side-by-side comparison."),
        (c2,"Broker Comparison","Filter and compare 13 CSE-registered stockbrokers by brokerage fee, minimum investment, online platform, and research support."),
        (c3,"Sector Analytics","Explore profitability, debt, and liquidity across 21 CSE sectors to understand macro-level investment context."),
    ]:
        col.markdown(f'<div class="section-card"><h3>{title}</h3><p style="color:#5a7199;font-size:0.87rem;margin-top:8px;">{desc}</p></div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# COMPANY ANALYSIS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Company Analysis":
    st.markdown(f'<div class="quote-banner">"{q_text}" &nbsp;— <strong>{q_author}</strong></div>', unsafe_allow_html=True)
    st.markdown("## Company Analysis")
    st.caption("Select up to 3 companies and choose your investor profile to see tailored analysis and scoring.")

    # ── Investor Type Selection ───────────────────────────────────────────────
    st.markdown("### Select Investor Type")
    inv_col1, inv_col2 = st.columns(2)
    with inv_col1:
        st.markdown("""
        <div class="section-card" style="border-left: 4px solid #0B1D51;">
            <h3 style="margin:0 0 6px 0;">Defensive Investor</h3>
            <p style="color:#5a7199; font-size:0.85rem; margin:0;">
            Uses <strong>10 years</strong> of data. Strictly evaluates long-term consistency —
            earnings, dividends, financial health, and conservative valuation.
            Based on Benjamin Graham's criteria for risk-averse, long-term investors.
            </p>
        </div>""", unsafe_allow_html=True)
    with inv_col2:
        st.markdown("""
        <div class="section-card" style="border-left: 4px solid #2563eb;">
            <h3 style="margin:0 0 6px 0;">Enterprising Investor</h3>
            <p style="color:#5a7199; font-size:0.85rem; margin:0;">
            Uses <strong>5 years</strong> of data. More flexible — evaluates financial strength,
            earnings stability, dividend payments, valuation metrics, and growth.
            Suited for active investors willing to take calculated risks.
            </p>
        </div>""", unsafe_allow_html=True)

    investor_type = st.radio(
        "Choose investor type",
        ["Defensive Investor (10 Years)", "Enterprising Investor (5 Years)"],
        horizontal=True,
        label_visibility="collapsed",
    )
    is_defensive = investor_type.startswith("Defensive")
    st.divider()

    # ── Company Selection ─────────────────────────────────────────────────────
    all_names = sorted(companies.keys())
    col1, col2, col3 = st.columns(3)
    with col1: c1 = st.selectbox("Company 1", ["— Select —"] + all_names, key="c1")
    with col2: c2 = st.selectbox("Company 2 (optional)", ["— Select —"] + all_names, key="c2")
    with col3: c3 = st.selectbox("Company 3 (optional)", ["— Select —"] + all_names, key="c3")

    selected = list(dict.fromkeys([c for c in [c1,c2,c3] if c != "— Select —"]))
    if len(selected) < len([c for c in [c1,c2,c3] if c != "— Select —"]):
        st.warning("Duplicate company removed. Please select different companies.")
    if not selected:
        st.info("Select at least one company above to begin analysis.")
        st.stop()

    st.divider()

    # ── Per-company dashboard ─────────────────────────────────────────────────
    score_summary = []  # for comparison

    for company_name in selected:
        fd = companies.get(company_name, {})
        if not fd:
            st.error(f"No data found for: {company_name}")
            continue

        # Run selected scoring engine
        if is_defensive:
            total_score, criteria = score_defensive(fd)
            score_type_label = "Defensive Score"
            data_note = "Analysis based on up to 10 years of data."
        else:
            total_score, criteria = score_enterprising(fd)
            score_type_label = "Enterprising Score"
            data_note = "Analysis based on the last 5 years of data."

        score_summary.append({"Company": company_name, "Score": total_score, "Type": score_type_label})

        # Pull chart data
        eps_s  = get_series(fd, "income_statement", "eps")
        rev_s  = get_series(fd, "income_statement", "total_revenue")
        div_s  = get_series(fd, "income_statement", "dividend_per_share")
        cr_s   = get_series(fd, "ratios", "current_ratio")
        dr_s   = get_series(fd, "ratios", "debt_ratio")
        mp_s   = get_series(fd, "market_metrics", "market_price")
        iv_s   = get_series(fd, "graham_analysis", "intrinsic_value")
        mos_s  = get_series(fd, "graham_analysis", "margin_of_safety")
        pe_s   = get_series(fd, "market_metrics", "pe_ratio")
        pb_s   = get_series(fd, "market_metrics", "pb_ratio")
        bv_s   = get_series(fd, "market_metrics", "bvps")
        rev_g  = get_series(fd, "growth", "revenue_growth_yoy")
        eps_g  = get_series(fd, "growth", "eps_growth_yoy")
        intang = get_series(fd, "balance_sheet", "intangible_assets")

        with st.expander(f"{company_name}  |  {fd.get('sector','—')}  |  {score_type_label}: {total_score}/100", expanded=True):

            # Header
            score_color = "#16a34a" if total_score >= 75 else "#d97706" if total_score >= 50 else "#dc2626"
            st.markdown(f"""
            <div class="company-header">
                <div style="font-size:1.05rem; font-weight:700;">{company_name} &nbsp;({fd.get('symbol','—')})</div>
                <div style="color:#90b8e0; font-size:0.82rem; margin-top:4px;">
                    {fd.get('sector','—')} &nbsp;|&nbsp; {fd.get('industry','—')} &nbsp;|&nbsp;
                    {score_type_label}: <strong style="color:#ffffff;">{total_score}/100</strong>
                    &nbsp;|&nbsp; <span style="font-style:italic;">{data_note}</span>
                </div>
            </div>""", unsafe_allow_html=True)

            # Key metrics row
            mk = st.columns(7)
            mk[0].metric("EPS",              fmt(latest(eps_s), "LKR "))
            mk[1].metric("Revenue",          fmt_large(latest(rev_s)))
            mk[2].metric("Dividend/Share",   fmt(latest(div_s), "LKR "))
            mk[3].metric("Book Value/Share", fmt(latest(bv_s), "LKR "))
            mk[4].metric("Intangibles",      fmt_large(latest(intang)))
            mk[5].metric("Current Ratio",    fmt(latest(cr_s)))
            mk[6].metric("Debt Ratio",       fmt(latest(dr_s)))

            st.markdown("")
            gk = st.columns(4)
            gk[0].metric("Market Price",     fmt(latest(mp_s), "LKR "))
            gk[1].metric("Intrinsic Value",  fmt(latest(iv_s), "LKR "))
            gk[2].metric("Margin of Safety", f"{latest(mos_s):.1%}" if latest(mos_s) is not None else "N/A")
            gk[3].metric("P/E Ratio",        fmt(latest(pe_s)))

            st.divider()

            # Score + Criteria
            sc_col, cr_col = st.columns([1, 3])
            with sc_col:
                render_score_card(total_score, score_type_label)
            with cr_col:
                st.markdown(f"**Criteria Breakdown — {investor_type}**")
                render_criteria(criteria)

            st.divider()

            # Charts
            ch1, ch2 = st.columns(2)
            with ch1:
                if eps_s: st.plotly_chart(line_chart({"EPS (LKR)": eps_s}, "Earnings Per Share Trend", "LKR"), use_container_width=True)
            with ch2:
                if rev_s:
                    rev_m = {y: v/1e6 for y,v in rev_s.items()}
                    st.plotly_chart(line_chart({"Revenue (LKR M)": rev_m}, "Revenue Trend", "LKR Millions"), use_container_width=True)

            ch3, ch4 = st.columns(2)
            with ch3:
                if cr_s and dr_s:
                    yrs = sorted(set(list(cr_s.keys()) + list(dr_s.keys())))
                    fig = go.Figure()
                    fig.add_trace(go.Bar(name="Current Ratio", x=yrs, y=[cr_s.get(y) for y in yrs], marker_color="#2563eb"))
                    fig.add_trace(go.Bar(name="Debt Ratio",    x=yrs, y=[dr_s.get(y) for y in yrs], marker_color="#dc2626"))
                    thresh = 2.0 if is_defensive else 1.5
                    fig.add_hline(y=thresh, line_dash="dash", line_color="#16a34a", annotation_text=f"CR Min {thresh}")
                    fig.update_layout(title=dict(text="Current Ratio vs Debt Ratio", font=dict(color="#0B1D51",size=13),x=0),
                        barmode="group", paper_bgcolor="#ffffff", plot_bgcolor="#F8F9FB", font=dict(color="#5a7199"),
                        xaxis=dict(gridcolor="#e5eaf2"), yaxis=dict(gridcolor="#e5eaf2"),
                        legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(l=10,r=10,t=40,b=10), height=285)
                    st.plotly_chart(fig, use_container_width=True)

            with ch4:
                if mp_s or iv_s:
                    all_yrs = sorted(set(list(mp_s.keys()) + list(iv_s.keys())))
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(name="Market Price",    x=all_yrs, y=[mp_s.get(y) for y in all_yrs], mode="lines+markers", line=dict(color="#d97706",width=2.5)))
                    fig.add_trace(go.Scatter(name="Intrinsic Value", x=all_yrs, y=[iv_s.get(y) for y in all_yrs], mode="lines+markers", line=dict(color="#16a34a",width=2.5,dash="dash")))
                    fig.update_layout(title=dict(text="Market Price vs Intrinsic Value",font=dict(color="#0B1D51",size=13),x=0),
                        paper_bgcolor="#ffffff", plot_bgcolor="#F8F9FB", font=dict(color="#5a7199"),
                        xaxis=dict(gridcolor="#e5eaf2"), yaxis=dict(gridcolor="#e5eaf2"),
                        legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(l=10,r=10,t=40,b=10), height=285)
                    st.plotly_chart(fig, use_container_width=True)

            ch5, ch6 = st.columns(2)
            with ch5:
                if div_s and eps_s:
                    yrs = sorted(set(list(div_s.keys()) + list(eps_s.keys())))
                    fig = go.Figure()
                    fig.add_trace(go.Bar(name="Dividend/Share", x=yrs, y=[div_s.get(y,0) or 0 for y in yrs], marker_color="#9333ea"))
                    fig.add_trace(go.Bar(name="EPS",            x=yrs, y=[eps_s.get(y,0) or 0 for y in yrs], marker_color="#2563eb"))
                    fig.update_layout(title=dict(text="Dividend vs EPS",font=dict(color="#0B1D51",size=13),x=0),
                        barmode="group", paper_bgcolor="#ffffff", plot_bgcolor="#F8F9FB", font=dict(color="#5a7199"),
                        xaxis=dict(gridcolor="#e5eaf2"), yaxis=dict(gridcolor="#e5eaf2"),
                        legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(l=10,r=10,t=40,b=10), height=285)
                    st.plotly_chart(fig, use_container_width=True)

            with ch6:
                if rev_g or eps_g:
                    all_yrs = sorted(set(list(rev_g.keys()) + list(eps_g.keys())))
                    fig = go.Figure()
                    if rev_g: fig.add_trace(go.Scatter(name="Revenue Growth YoY", x=all_yrs, y=[rev_g.get(y) for y in all_yrs], mode="lines+markers", line=dict(color="#0B1D51",width=2)))
                    if eps_g: fig.add_trace(go.Scatter(name="EPS Growth YoY",     x=all_yrs, y=[eps_g.get(y) for y in all_yrs], mode="lines+markers", line=dict(color="#2563eb",width=2,dash="dot")))
                    fig.add_hline(y=0, line_color="#dc2626", line_dash="dash")
                    fig.update_layout(title=dict(text="Year-on-Year Growth Rates",font=dict(color="#0B1D51",size=13),x=0),
                        paper_bgcolor="#ffffff", plot_bgcolor="#F8F9FB", font=dict(color="#5a7199"),
                        xaxis=dict(gridcolor="#e5eaf2"), yaxis=dict(gridcolor="#e5eaf2", tickformat=".0%"),
                        legend=dict(bgcolor="rgba(0,0,0,0)"), margin=dict(l=10,r=10,t=40,b=10), height=285)
                    st.plotly_chart(fig, use_container_width=True)

            # Raw data table
            with st.expander("View Full Data Table"):
                years = sorted(fd.get("years",[]), reverse=True)
                rows = []
                for y in years:
                    rows.append({"Year":y, "EPS":eps_s.get(y), "Revenue":fmt_large(rev_s.get(y)),
                        "Dividend/Share":div_s.get(y), "Market Price":mp_s.get(y),
                        "Book Value/Share":bv_s.get(y), "Intrinsic Value":iv_s.get(y),
                        "Margin of Safety":mos_s.get(y), "Current Ratio":cr_s.get(y),
                        "Debt Ratio":dr_s.get(y), "P/E":pe_s.get(y), "P/B":pb_s.get(y)})
                st.dataframe(pd.DataFrame(rows).set_index("Year"), use_container_width=True)

    # ── Comparison ────────────────────────────────────────────────────────────
    if len(selected) > 1:
        st.divider()
        st.markdown("## Side-by-Side Comparison")

        # Score bar chart
        if score_summary:
            sc_colors = ["#16a34a" if s["Score"]>=75 else "#d97706" if s["Score"]>=50 else "#dc2626" for s in score_summary]
            fig_sc = go.Figure(go.Bar(
                x=[s["Company"] for s in score_summary],
                y=[s["Score"]   for s in score_summary],
                marker_color=sc_colors,
                text=[f"{s['Score']}/100" for s in score_summary],
                textposition="outside", textfont=dict(color="#0B1D51", size=13, family="Arial Black"),
            ))
            fig_sc.add_hline(y=75, line_dash="dash", line_color="#16a34a", annotation_text="Strong (75)")
            fig_sc.add_hline(y=50, line_dash="dash", line_color="#d97706", annotation_text="Moderate (50)")
            fig_sc.update_layout(
                title=dict(text=f"Score Comparison — {investor_type}", font=dict(color="#0B1D51",size=14),x=0),
                paper_bgcolor="#ffffff", plot_bgcolor="#F8F9FB", font=dict(color="#5a7199"),
                xaxis=dict(gridcolor="#e5eaf2"), yaxis=dict(gridcolor="#e5eaf2", range=[0,115]),
                margin=dict(l=10,r=10,t=40,b=10), height=320)
            st.plotly_chart(fig_sc, use_container_width=True)

        # Metrics comparison table
        rows = []
        for name in selected:
            fd = companies.get(name,{})
            score = next((s["Score"] for s in score_summary if s["Company"]==name), "N/A")
            rows.append({
                "Company":          name,
                "Sector":           fd.get("sector","—"),
                f"{score_type_label}": f"{score}/100",
                "EPS":              fmt(latest(get_series(fd,"income_statement","eps")), "LKR "),
                "Revenue":          fmt_large(latest(get_series(fd,"income_statement","total_revenue"))),
                "Dividend/Share":   fmt(latest(get_series(fd,"income_statement","dividend_per_share")), "LKR "),
                "Book Value/Share": fmt(latest(get_series(fd,"market_metrics","bvps")), "LKR "),
                "Current Ratio":    fmt(latest(get_series(fd,"ratios","current_ratio"))),
                "Debt Ratio":       fmt(latest(get_series(fd,"ratios","debt_ratio"))),
                "Market Price":     fmt(latest(get_series(fd,"market_metrics","market_price")), "LKR "),
                "Intrinsic Value":  fmt(latest(get_series(fd,"graham_analysis","intrinsic_value")), "LKR "),
                "Margin of Safety": f"{latest(get_series(fd,'graham_analysis','margin_of_safety')):.1%}" if latest(get_series(fd,"graham_analysis","margin_of_safety")) is not None else "N/A",
                "P/E Ratio":        fmt(latest(get_series(fd,"market_metrics","pe_ratio"))),
                "P/B Ratio":        fmt(latest(get_series(fd,"market_metrics","pb_ratio"))),
            })
        df_cmp = pd.DataFrame(rows).set_index("Company")
        st.dataframe(df_cmp.T, use_container_width=True)

        # Radar chart
        st.markdown("### Comparative Radar")
        def norm(val, lo, hi):
            if val is None: return 0
            return max(0, min(10, (val-lo)/(hi-lo)*10))

        rlabels = ["Score/10","EPS","Current Ratio","Div/Share","Margin of Safety"]
        fig_r = go.Figure()
        for i, name in enumerate(selected):
            fd = companies.get(name,{})
            sc = next((s["Score"] for s in score_summary if s["Company"]==name), 0)
            vals = [
                sc/10,
                norm(latest(get_series(fd,"income_statement","eps")), -5, 50),
                norm(latest(get_series(fd,"ratios","current_ratio")), 0, 5),
                norm(latest(get_series(fd,"income_statement","dividend_per_share")), 0, 20),
                norm(latest(get_series(fd,"graham_analysis","margin_of_safety")), -1, 1),
            ]
            fig_r.add_trace(go.Scatterpolar(r=vals+[vals[0]], theta=rlabels+[rlabels[0]],
                fill="toself", name=name, line=dict(color=C[i%len(C)]), opacity=0.7))
        fig_r.update_layout(
            polar=dict(bgcolor="#F8F9FB",
                radialaxis=dict(visible=True, range=[0,10], gridcolor="#e5eaf2", color="#5a7199"),
                angularaxis=dict(gridcolor="#e5eaf2", color="#0B1D51")),
            paper_bgcolor="#ffffff", font=dict(color="#5a7199"),
            legend=dict(bgcolor="rgba(0,0,0,0)", font=dict(color="#0B1D51")), height=420)
        st.plotly_chart(fig_r, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# BROKER COMPARISON
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Broker Comparison":
    st.markdown("## Broker Comparison")
    st.caption("Compare 13 CSE-registered stockbrokers on fees, minimum investment, platform, and research support.")

    df_b = pd.DataFrame(brokers)
    def parse_min(val):
        try: return float(str(val).replace(",","").replace(" ",""))
        except: return 0.0
    df_b["min_numeric"] = df_b["min_investment_raw"].apply(parse_min)

    fc1, fc2 = st.columns(2)
    with fc1:
        max_inv = int(df_b["min_numeric"].max()) or 1000000
        dep_filter = st.slider("Maximum Minimum Investment (LKR)", 0, max_inv, max_inv, step=50000)
    with fc2:
        platforms = ["All"] + sorted(df_b["online_platform"].dropna().unique().tolist())
        plat_filter = st.selectbox("Online Platform", platforms)

    filtered = df_b[df_b["min_numeric"] <= dep_filter]
    if plat_filter != "All":
        filtered = filtered[filtered["online_platform"] == plat_filter]

    st.markdown(f"**{len(filtered)} broker(s) match your filters.**")
    st.divider()

    col_map = {"name":"Broker","brokerage_fee_percent":"Fee %","min_investment_raw":"Min Investment",
               "online_platform":"Platform","research_support":"Research Support"}
    show_cols = [c for c in col_map if c in filtered.columns]
    df_show = filtered[show_cols].copy(); df_show.columns = [col_map[c] for c in show_cols]
    st.dataframe(df_show.reset_index(drop=True), use_container_width=True)
    st.divider()

    ch1, ch2 = st.columns(2)
    with ch1:
        st.markdown("### Brokerage Fee (%)")
        df_fee = filtered.dropna(subset=["brokerage_fee_percent"]).sort_values("brokerage_fee_percent")
        min_fee = df_fee["brokerage_fee_percent"].min()
        colors_fee = ["#16a34a" if v==min_fee else "#0B1D51" for v in df_fee["brokerage_fee_percent"]]
        fig = go.Figure(go.Bar(x=df_fee["brokerage_fee_percent"], y=df_fee["name"], orientation="h",
            marker_color=colors_fee, text=[f"{v}%" for v in df_fee["brokerage_fee_percent"]],
            textposition="outside", textfont=dict(color="#5a7199",size=10)))
        fig.update_layout(paper_bgcolor="#ffffff", plot_bgcolor="#F8F9FB", font=dict(color="#5a7199"),
            xaxis=dict(gridcolor="#e5eaf2",title="Fee %"), yaxis=dict(gridcolor="#e5eaf2"),
            margin=dict(l=10,r=10,t=20,b=10), height=max(300,len(df_fee)*40))
        st.plotly_chart(fig, use_container_width=True)
        st.caption("Green = lowest fee.")
    with ch2:
        st.markdown("### Minimum Investment (LKR)")
        df_inv = filtered[filtered["min_numeric"]>0].sort_values("min_numeric")
        if not df_inv.empty:
            fig = go.Figure(go.Bar(x=df_inv["min_numeric"], y=df_inv["name"], orientation="h",
                marker_color="#2563eb", text=[f"LKR {v:,.0f}" for v in df_inv["min_numeric"]],
                textposition="outside", textfont=dict(color="#5a7199",size=10)))
            fig.update_layout(paper_bgcolor="#ffffff", plot_bgcolor="#F8F9FB", font=dict(color="#5a7199"),
                xaxis=dict(gridcolor="#e5eaf2",title="LKR"), yaxis=dict(gridcolor="#e5eaf2"),
                margin=dict(l=10,r=10,t=20,b=10), height=max(300,len(df_inv)*40))
            st.plotly_chart(fig, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# SECTOR ANALYTICS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Sector Analytics":
    st.markdown("## Sector Analytics")
    st.caption("Macro-level financial overview across 21 CSE sectors.")

    sector_rows = []
    for sec_name, sec_info in sectors.items():
        sec_cos = sec_info.get("companies",[])
        eps_l,rev_l,dr_l,cr_l,mos_l = [],[],[],[],[]
        for cname in sec_cos:
            fd = companies.get(cname,{})
            if not fd: continue
            for lst,keys in [(eps_l,("income_statement","eps")),(rev_l,("income_statement","total_revenue")),
                             (dr_l,("ratios","debt_ratio")),(cr_l,("ratios","current_ratio")),
                             (mos_l,("graham_analysis","margin_of_safety"))]:
                v = latest(get_series(fd,*keys))
                if v is not None: lst.append(v)
        def avg(lst): return round(sum(lst)/len(lst),3) if lst else None
        sector_rows.append({"Sector":sec_name,"Companies":len(sec_cos),
            "Avg EPS (LKR)":avg(eps_l),"Avg Revenue (LKR M)":round(avg(rev_l)/1e6,1) if avg(rev_l) else None,
            "Avg Debt Ratio":avg(dr_l),"Avg Current Ratio":avg(cr_l),"Avg Margin of Safety":avg(mos_l)})

    df_sec = pd.DataFrame(sector_rows).dropna(subset=["Avg EPS (LKR)"]).sort_values("Avg EPS (LKR)",ascending=False)
    sel_secs = st.multiselect("Filter to specific sectors (leave blank for all)", df_sec["Sector"].tolist())
    if sel_secs: df_sec = df_sec[df_sec["Sector"].isin(sel_secs)]

    tab1,tab2,tab3,tab4,tab5 = st.tabs(["EPS by Sector","Revenue","Debt Levels","Liquidity","Full Table"])

    with tab1:
        df_p = df_sec.sort_values("Avg EPS (LKR)")
        colors = ["#dc2626" if v<0 else "#0B1D51" for v in df_p["Avg EPS (LKR)"]]
        fig = go.Figure(go.Bar(x=df_p["Avg EPS (LKR)"], y=df_p["Sector"], orientation="h", marker_color=colors,
            text=[f"LKR {v:.2f}" for v in df_p["Avg EPS (LKR)"]], textposition="outside", textfont=dict(color="#5a7199",size=9)))
        fig.update_layout(paper_bgcolor="#ffffff",plot_bgcolor="#F8F9FB",font=dict(color="#5a7199"),
            xaxis=dict(gridcolor="#e5eaf2",title="Avg EPS (LKR)"),yaxis=dict(gridcolor="#e5eaf2"),
            height=max(350,len(df_p)*30),margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig,use_container_width=True)

    with tab2:
        df_p = df_sec.dropna(subset=["Avg Revenue (LKR M)"]).sort_values("Avg Revenue (LKR M)",ascending=False)
        fig = go.Figure(go.Bar(x=df_p["Sector"],y=df_p["Avg Revenue (LKR M)"],marker_color="#2563eb",
            text=[f"LKR {v:.1f}M" for v in df_p["Avg Revenue (LKR M)"]],textposition="outside",textfont=dict(color="#5a7199",size=9)))
        fig.update_layout(paper_bgcolor="#ffffff",plot_bgcolor="#F8F9FB",font=dict(color="#5a7199"),
            xaxis=dict(gridcolor="#e5eaf2",tickangle=-35),yaxis=dict(gridcolor="#e5eaf2"),
            height=400,margin=dict(l=10,r=10,t=20,b=80))
        st.plotly_chart(fig,use_container_width=True)

    with tab3:
        df_p = df_sec.dropna(subset=["Avg Debt Ratio"]).sort_values("Avg Debt Ratio")
        colors = ["#16a34a" if v<0.4 else "#d97706" if v<0.6 else "#dc2626" for v in df_p["Avg Debt Ratio"]]
        fig = go.Figure(go.Bar(x=df_p["Avg Debt Ratio"],y=df_p["Sector"],orientation="h",marker_color=colors,
            text=[f"{v:.3f}" for v in df_p["Avg Debt Ratio"]],textposition="outside",textfont=dict(color="#5a7199",size=9)))
        fig.add_vline(x=0.4,line_dash="dash",line_color="#16a34a",annotation_text="Safe < 0.4")
        fig.add_vline(x=0.6,line_dash="dash",line_color="#dc2626",annotation_text="Risky > 0.6")
        fig.update_layout(paper_bgcolor="#ffffff",plot_bgcolor="#F8F9FB",font=dict(color="#5a7199"),
            xaxis=dict(gridcolor="#e5eaf2"),yaxis=dict(gridcolor="#e5eaf2"),
            height=max(350,len(df_p)*30),margin=dict(l=10,r=10,t=20,b=10))
        st.plotly_chart(fig,use_container_width=True)

    with tab4:
        df_p = df_sec.dropna(subset=["Avg Current Ratio"]).sort_values("Avg Current Ratio",ascending=False)
        colors = ["#16a34a" if v>=1.5 else "#d97706" if v>=1 else "#dc2626" for v in df_p["Avg Current Ratio"]]
        fig = go.Figure(go.Bar(x=df_p["Sector"],y=df_p["Avg Current Ratio"],marker_color=colors,
            text=[f"{v:.2f}" for v in df_p["Avg Current Ratio"]],textposition="outside",textfont=dict(color="#5a7199",size=9)))
        fig.add_hline(y=1.5,line_dash="dash",line_color="#0B1D51",annotation_text="Target 1.5")
        fig.update_layout(paper_bgcolor="#ffffff",plot_bgcolor="#F8F9FB",font=dict(color="#5a7199"),
            xaxis=dict(gridcolor="#e5eaf2",tickangle=-35),yaxis=dict(gridcolor="#e5eaf2"),
            height=400,margin=dict(l=10,r=10,t=20,b=80))
        st.plotly_chart(fig,use_container_width=True)

    with tab5:
        st.dataframe(df_sec.reset_index(drop=True),use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# EDUCATIONAL PORTAL
# ══════════════════════════════════════════════════════════════════════════════
elif page == "Educational Portal":
    st.markdown("## Educational Portal")
    st.caption("Understand the key metrics behind Graham-style value investing.")

    inv_tab1, inv_tab2, inv_tab3 = st.tabs(["Defensive Investor Criteria", "Enterprising Investor Criteria", "Key Metrics Explained"])

    with inv_tab1:
        st.markdown("### Defensive Investor — 7 Criteria (100 Points Total)")
        st.caption("Uses 10 years of data. Suited for risk-averse, long-term investors.")
        criteria_def = [
            ("Earnings Consistency","20 pts","Positive EPS for all of the last 10 years with no deficits."),
            ("Dividend History","15 pts","Uninterrupted dividend payments for at least 10 years."),
            ("Financial Health — Current Ratio >= 2.0","15 pts","Current ratio of at least 2.0 to ensure strong short-term liquidity."),
            ("Low Debt — Debt Ratio < 0.5","10 pts","Low debt-to-asset ratio to ensure financial stability during downturns."),
            ("Valuation Limits (P/E)","15 pts","Not more than 20x last 12-month earnings or 25x 7-year average earnings."),
            ("Margin of Safety >= 33%","15 pts","Buy at a price significantly below intrinsic value to protect against error and market swings."),
            ("Company Quality","10 pts","Positive book value and consistent positive revenue — large, established company."),
        ]
        for name, pts, desc in criteria_def:
            st.markdown(f"""
            <div style="display:flex;align-items:flex-start;gap:14px;padding:10px 0;border-bottom:1px solid #f1f5f9;">
                <div style="flex:1;">
                    <span style="font-weight:700;color:#0B1D51;font-size:0.9rem;">{name}</span>
                    <span style="color:#5a7199;font-size:0.82rem;"> — {desc}</span>
                </div>
                <div style="color:#2563eb;font-weight:700;font-size:0.85rem;white-space:nowrap;">{pts}</div>
            </div>""", unsafe_allow_html=True)

    with inv_tab2:
        st.markdown("### Enterprising Investor — 5 Criteria (100 Points Total)")
        st.caption("Uses 5 years of data. Suited for active investors willing to take calculated risks.")
        criteria_ent = [
            ("Financial Strength","25 pts","Current ratio > 1.5 and long-term debt < 110% of working capital."),
            ("Earnings Stability","20 pts","Positive EPS for each of the last 5 years."),
            ("Dividend Record","15 pts","Company pays some level of dividends — signals shareholder-friendly management."),
            ("Valuation (P/E <= 15, P/B <= 1.5)","25 pts","P/E below 10–15 and P/B below 1.2–1.5 to signal undervaluation."),
            ("Earnings Growth","15 pts","Demonstrated EPS growth over the past 5 years."),
        ]
        for name, pts, desc in criteria_ent:
            st.markdown(f"""
            <div style="display:flex;align-items:flex-start;gap:14px;padding:10px 0;border-bottom:1px solid #f1f5f9;">
                <div style="flex:1;">
                    <span style="font-weight:700;color:#0B1D51;font-size:0.9rem;">{name}</span>
                    <span style="color:#5a7199;font-size:0.82rem;"> — {desc}</span>
                </div>
                <div style="color:#2563eb;font-weight:700;font-size:0.85rem;white-space:nowrap;">{pts}</div>
            </div>""", unsafe_allow_html=True)

    with inv_tab3:
        topics = [
            ("EPS — Earnings Per Share","EPS = Net Profit / Shares Outstanding",
             "Measures profit per share. Graham required 10 years of uninterrupted positive EPS for defensive investors.",
             [("EPS > 5","Strong","tag-good"),("EPS > 0","Positive","tag-ok"),("EPS < 0","Avoid","tag-bad")]),
            ("Book Value Per Share","BVPS = (Total Assets - Intangibles - Liabilities) / Shares Outstanding",
             "Net asset value per share. Graham preferred stocks below 1.5x book value.",
             [("P/B < 1.5","Undervalued","tag-good"),("P/B 1.5-3","Fair","tag-ok"),("P/B > 3","Overvalued","tag-bad")]),
            ("Margin of Safety","MoS = (Intrinsic Value - Market Price) / Intrinsic Value",
             "Graham's core principle: always buy below intrinsic value. Recommended at least 33%.",
             [("MoS > 33%","Strong safety","tag-good"),("MoS 0-33%","Some safety","tag-ok"),("MoS < 0%","Overvalued","tag-bad")]),
            ("Current Ratio","Current Ratio = Current Assets / Current Liabilities",
             "Graham required a minimum of 2.0 for defensive investors and 1.5 for enterprising investors.",
             [("CR >= 2.0","Defensive pass","tag-good"),("CR >= 1.5","Enterprising pass","tag-ok"),("CR < 1.0","Fail","tag-bad")]),
            ("Debt Ratio","Debt Ratio = Total Debt / Total Assets",
             "Lower is safer. Graham warned against excessive leverage relative to equity.",
             [("DR < 0.4","Low leverage","tag-good"),("DR 0.4-0.6","Moderate","tag-ok"),("DR > 0.6","High risk","tag-bad")]),
            ("Intrinsic Value","IV = sqrt(22.5 x EPS x BVPS)",
             "Graham's formula to estimate true worth. Compare to market price to find undervalued stocks.",
             [("Price < IV","Potential buy","tag-good"),("Price ~ IV","Fair","tag-ok"),("Price > IV","Overvalued","tag-bad")]),
        ]
        for title, formula, tip, thresholds in topics:
            with st.expander(title):
                l, r = st.columns([3,1])
                with l:
                    st.code(formula, language="text")
                    st.info(f"Graham Principle: {tip}")
                with r:
                    st.markdown("**Thresholds**")
                    for label, verdict, cls in thresholds:
                        st.markdown(f'<span class="{cls}">{label}: {verdict}</span><br>', unsafe_allow_html=True)

# ── Footer ────────────────────────────────────────────────────────────────────
st.markdown('<div class="footer">Investor 360 &nbsp;|&nbsp; Colombo Stock Exchange &nbsp;|&nbsp; Data: 2016–2025</div>', unsafe_allow_html=True)
