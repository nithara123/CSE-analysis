"""
investor360_app.py — Investor 360 (redesigned)
====================================
Thin orchestration layer only. All calculations live in graham_engine.py
(untouched Graham logic) and ai_engine.py (new AI Recommendation Score).
All page content lives in pages/*.py. This file's job is: load data once,
gate on onboarding, render the sidebar, and route to the selected page.

Architecture map (what changed vs. the original single-file app.py):

    ORIGINAL                          REDESIGNED
    ---------------------------------  -----------------------------------
    app.py (everything)                app.py (routing/orchestration only)
    score_defensive/score_enterprising graham_engine.py (byte-identical)
    (n/a - new requirement)            ai_engine.py (AI Recommendation Score)
    (n/a - new requirement)            preferences.py + onboarding.py
    (n/a - new requirement)            portfolio_store.py
    inline metric numbers, no context  metric_info.py + render_metric_info()
    Home / Company Analysis / ...      pages/dashboard.py, discover.py,
                                        workspace.py, portfolio.py, etc.
    cse_price_chart.py                 unchanged, reused as-is
    news_intelligence.py               unchanged, reused as-is
    investor360_data.json              unchanged, reused as-is
"""

import json

import streamlit as st

from preferences import load_profile, reset_onboarding
from onboarding import render_onboarding
from app_pages import dashboard, getting_started, discover, workspace, portfolio, market_dashboard, learning_centre

st.set_page_config(page_title="Investor 360 | CSE Analytics", layout="wide", initial_sidebar_state="expanded")

# ── CSS (unchanged "Ledger" theme from the original app) ──────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sora:wght@600;700;800&family=Inter:wght@400;500;600;700&display=swap');

:root {
    --bg: #F3F4FC; --surface: #FFFFFF; --surface-alt: #EEF0FB;
    --ink: #15172E; --ink-soft: #8B93AD;
    --indigo: #4F46E5; --indigo-deep: #372FA0;
    --teal: #14B8A6; --coral: #FB6A5B; --amber: #F5A524;
    --radius: 20px;
    --shadow: 0 8px 24px rgba(21, 23, 46, 0.06);
    --shadow-sm: 0 2px 10px rgba(21, 23, 46, 0.05);
}
html, body, .stApp { background-color: var(--bg) !important; color: var(--ink); font-family: 'Inter', sans-serif; }
header[data-testid="stHeader"] { background: transparent; }
.block-container { padding-top: 1.75rem; padding-bottom: 2rem; }

section[data-testid="stSidebar"] { background-color: var(--surface); border-right: 1px solid #E5E8F5; }
section[data-testid="stSidebar"] * { color: var(--ink) !important; }
section[data-testid="stSidebar"] h2 { font-family: 'Sora', sans-serif !important; font-weight: 800 !important; color: var(--indigo) !important; letter-spacing: -0.02em; }
section[data-testid="stSidebar"] div[role="radiogroup"] { gap: 6px; display: flex; flex-direction: column; }
section[data-testid="stSidebar"] div[role="radiogroup"] label {
    background: var(--surface-alt); border-radius: 999px; padding: 9px 16px; margin: 0;
    font-weight: 600; font-size: 0.85rem; transition: all 0.15s ease; border: 1px solid transparent;
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:hover { border-color: var(--indigo); }
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) {
    background: var(--indigo) !important; box-shadow: var(--shadow-sm);
}
section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked) p { color: #FFFFFF !important; }

h1, h2, h3 { font-family: 'Sora', sans-serif !important; letter-spacing: -0.02em; }
h1 { color: var(--ink) !important; font-size: 2rem !important; font-weight: 800 !important; }
h2 { color: var(--ink) !important; font-size: 1.35rem !important; font-weight: 700 !important; }
h3 { color: var(--ink) !important; font-size: 1.02rem !important; font-weight: 700 !important; }
h2::before, h3::before { content:""; display:inline-block; width:4px; height:1em; background:var(--teal); border-radius:3px; margin-right:9px; vertical-align:-0.1em; }

[data-testid="metric-container"] { background: var(--surface); border: 1px solid #EAEDF7; border-radius: var(--radius); padding: 18px; box-shadow: var(--shadow-sm); }
[data-testid="metric-container"] label { color: var(--ink-soft) !important; font-size: 0.72rem; font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; }
[data-testid="metric-container"] [data-testid="metric-value"] { color: var(--ink) !important; font-family: 'Sora', sans-serif; font-size: 1.25rem !important; font-weight: 700; }

.quote-banner { background: linear-gradient(120deg, var(--indigo), #7C6FF0); border-radius: var(--radius); padding: 16px 24px; margin-bottom: 20px; font-style: italic; color: #EDEBFF; font-size: 0.94rem; box-shadow: var(--shadow); }

.section-card { background: var(--surface); border-radius: var(--radius); padding: 22px; margin-bottom: 16px; border: 1px solid #EAEDF7; box-shadow: var(--shadow-sm); transition: box-shadow 0.15s ease; }
.section-card:hover { box-shadow: var(--shadow); }

.tag-good { background:#DCFCF5; color:#0F7A6C; padding:3px 12px; border-radius:999px; font-size:0.76rem; font-weight:700; }
.tag-ok   { background:#FEF3D9; color:#9A6B0C; padding:3px 12px; border-radius:999px; font-size:0.76rem; font-weight:700; }
.tag-bad  { background:#FFE4E1; color:#C43D2E; padding:3px 12px; border-radius:999px; font-size:0.76rem; font-weight:700; }

.stTabs [data-baseweb="tab-list"] { background: var(--surface-alt); border-radius: 999px; padding: 4px; gap: 2px; }
.stTabs [role="tab"] { color: var(--ink-soft); font-weight: 600; font-size: 0.86rem; border-radius: 999px !important; padding: 6px 18px !important; }
.stTabs [role="tab"][aria-selected="true"] { color: #FFFFFF; background: var(--indigo) !important; border-bottom: none !important; }

.stSelectbox label, .stSlider label, .stMultiSelect label, .stRadio label { color: var(--ink) !important; font-weight: 600; font-size: 0.84rem; }

.company-header { background: linear-gradient(120deg, var(--ink) 0%, var(--indigo-deep) 100%); border-radius: var(--radius); padding: 18px 24px; margin-bottom: 16px; color: white; box-shadow: var(--shadow); }

.score-block { background: var(--surface); border-radius: var(--radius); padding: 22px; border: 1px solid #EAEDF7; text-align: center; box-shadow: var(--shadow-sm); }
.score-num { font-family: 'Sora', sans-serif; font-size: 2.9rem; font-weight: 800; line-height: 1; }
.score-label { font-size: 0.74rem; color: var(--ink-soft); text-transform: uppercase; letter-spacing: 0.07em; margin-top: 6px; font-weight: 700; }
.score-verdict { font-size: 0.87rem; font-weight: 700; margin-top: 10px; }

.criteria-row { display: flex; align-items: flex-start; gap: 12px; padding: 11px 0; border-bottom: 1px solid var(--surface-alt); }
.criteria-icon { font-size: 1rem; min-width: 22px; margin-top: 1px; }
.criteria-name { font-weight: 700; color: var(--ink); font-size: 0.88rem; }
.criteria-detail { color: var(--ink-soft); font-size: 0.82rem; margin-top: 2px; }
.criteria-pts { font-size: 0.8rem; color: var(--indigo); font-weight: 700; margin-left: auto; white-space: nowrap; padding-left: 12px; }

.footer { text-align:center; color: var(--ink-soft); font-size:0.78rem; padding:24px 0 8px 0; border-top:1px solid var(--surface-alt); margin-top:40px; }

.broker-card { background: var(--surface); border:1px solid #EAEDF7; border-radius: var(--radius); padding:18px; margin-bottom:10px; text-align:center; box-shadow: var(--shadow-sm); transition: transform 0.15s ease, box-shadow 0.15s ease; }
.broker-card:hover { transform: translateY(-2px); box-shadow: var(--shadow); }
.broker-avatar { width:56px; height:56px; border-radius:50%; object-fit:cover; border:2px solid var(--surface-alt); margin:0 auto 10px auto; display:block; background: var(--surface); }
.broker-name { font-weight:700; color: var(--ink); font-size:0.86rem; line-height:1.25; font-family: 'Sora', sans-serif; min-height:42px; display:flex; align-items:center; justify-content:center; }
.broker-fee  { color: var(--teal); font-weight: 700; font-size:0.78rem; margin:4px 0 10px 0; }
.broker-contact { color: var(--ink-soft); font-size:0.74rem; text-align:left; margin-top:8px; line-height:1.6; }
.broker-detail-panel { background: var(--surface); border:1px solid #EAEDF7; border-radius: var(--radius); padding:22px; box-shadow: var(--shadow); position:sticky; top:12px; }
.broker-badge { display:inline-block; background: var(--surface-alt); color: var(--indigo); font-size:0.7rem; font-weight:700; padding:3px 12px; border-radius:999px; margin-top:2px; }
.broker-detail-avatar { width:54px; height:54px; border-radius:50%; object-fit:cover; border:2px solid var(--surface-alt); float:left; margin-right:12px; }
.broker-min-box { background:#DCFCF5; color:#0F7A6C; border-radius:12px; padding:10px 14px; font-weight:700; font-size:0.9rem; margin-top:6px; }

.stButton button { border-radius: 999px !important; font-weight: 600 !important; border: 1px solid #EAEDF7 !important; }
.stButton button:hover { border-color: var(--indigo) !important; color: var(--indigo) !important; }
</style>
""", unsafe_allow_html=True)


# ── Load Data (unchanged JSON structure/location) ─────────────────────────────
@st.cache_data
def load_data():
    with open("investor360_data (3) (1) (1).json", "r", encoding="utf-8") as f:
        return json.load(f)


data = load_data()
companies = data.get("companies", {})
brokers = data.get("brokers", [])
sectors = data.get("sectors", {})

# The counts shown around the app (Dashboard metrics, sidebar summary) must
# always reflect what's actually in the loaded data, not a stale number that
# was hand-typed into the JSON's "meta" block at some earlier point. Recompute
# them here, once, so every page that reads data["meta"][...] gets the truth.
data.setdefault("meta", {})
data["meta"]["total_companies"] = len(companies)
data["meta"]["total_brokers"] = len(brokers)
data["meta"]["total_sectors"] = len(sectors)


# ── Onboarding gate ────────────────────────────────────────────────────────────
profile = load_profile()
if not profile.get("onboarding_complete"):
    render_onboarding()
    st.stop()

if st.session_state.pop("just_onboarded", False):
    st.toast("You're all set! Welcome to Investor 360.", icon="🎉")


# ── Navigation ─────────────────────────────────────────────────────────────────
NAV_PAGES = [
    "Dashboard", "Getting Started", "Discover Companies",
    "Company Workspace", "Portfolio", "Market Dashboard", "Learning Centre",
]

if "current_page" not in st.session_state:
    st.session_state.current_page = st.session_state.pop("pending_nav", "Dashboard")


def go_to(page_name):
    st.session_state.current_page = page_name
    st.rerun()


with st.sidebar:
    st.markdown("## Investor 360")
    st.markdown("*Colombo Stock Exchange Analytics*")
    st.divider()
    # Two different session_state keys are involved here on purpose:
    #   - "current_page": a plain variable, not tied to any widget. go_to()
    #     (called from buttons all over the app, e.g. "Getting Started
    #     Guide") writes to THIS one, and it's always safe to write to at
    #     any point in the script.
    #   - "nav_radio": the radio widget's own key. Streamlit will raise a
    #     StreamlitAPIException if you write to a widget's key AFTER that
    #     widget has already been drawn in the same script run - which is
    #     exactly what happened when current_page and the widget key were
    #     the same thing (go_to() runs deep inside a page, i.e. after the
    #     sidebar has already rendered this run).
    # The fix: sync nav_radio FROM current_page right here, immediately
    # before the widget is created - never after. That's the one point in
    # the script where it's legal to set it, and it's exactly what makes a
    # go_to() call from a button actually change what the radio shows.
    if st.session_state.get("nav_radio") != st.session_state.current_page:
        st.session_state.nav_radio = st.session_state.current_page

    page = st.radio(
        "", NAV_PAGES, label_visibility="collapsed",
        key="nav_radio",
    )
    if page != st.session_state.current_page:
        st.session_state.current_page = page
        st.rerun()

    st.divider()
    st.markdown(f"""
    <div style='font-size:0.8rem; color:#8B93AD;'>
    Companies: {data['meta']['total_companies']}<br>
    Brokers: {data['meta']['total_brokers']}<br>
    Sectors: {data['meta']['total_sectors']}<br>
    Data: {data['meta']['data_years']}
    </div>""", unsafe_allow_html=True)

    st.divider()
    with st.expander("Settings"):
        st.caption(f"Investor type: {profile.get('investor_type') or '—'}")
        st.caption(f"Risk appetite: {profile.get('risk_appetite') or '—'}")
        st.caption(f"Goal: {profile.get('investment_goal') or '—'}")
        if st.button("Reset onboarding"):
            reset_onboarding()
            st.session_state.current_page = "Dashboard"
            st.rerun()


# ── Route ──────────────────────────────────────────────────────────────────────
current = st.session_state.current_page

if current == "Dashboard":
    dashboard.render(data, companies, sectors, profile, go_to)
elif current == "Getting Started":
    getting_started.render(data, companies, sectors, brokers, profile)
elif current == "Discover Companies":
    discover.render(data, companies, sectors, profile, go_to)
elif current == "Company Workspace":
    workspace.render(data, companies, sectors, profile, go_to)
elif current == "Portfolio":
    portfolio.render(data, companies, sectors, profile, go_to)
elif current == "Market Dashboard":
    market_dashboard.render(data, companies, sectors, profile)
elif current == "Learning Centre":
    learning_centre.render(data, companies, sectors, profile)

st.markdown('<div class="footer">Investor 360 &nbsp;|&nbsp; Colombo Stock Exchange &nbsp;|&nbsp; Data: 2016–2025</div>', unsafe_allow_html=True)
