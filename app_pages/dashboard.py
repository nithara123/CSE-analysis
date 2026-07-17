"""
pages/dashboard.py
-------------------
The Dashboard is the app's landing page after onboarding. It deliberately
does NOT dump raw charts on a first-time user - it summarises portfolio
health, a couple of quick market facts, and (if the user opted in during
onboarding) a short list of AI-recommended companies to explore next.
"""

import random
import streamlit as st

from graham_engine import get_series, latest, fmt, score_defensive, score_enterprising, available_years
from ai_engine import compute_ai_recommendation
from ui_components import recommendation_pill, risk_pill
from investor_profile import resolve_investor_type
from portfolio_store import load_portfolio

QUOTES = [
    ("Price is what you pay. Value is what you get.", "Warren Buffett"),
    ("The intelligent investor is a realist who sells to optimists and buys from pessimists.", "Benjamin Graham"),
    ("An investment in knowledge pays the best interest.", "Benjamin Franklin"),
    ("Know what you own, and know why you own it.", "Peter Lynch"),
    ("Risk comes from not knowing what you are doing.", "Warren Buffett"),
]


def _quote():
    if "quote" not in st.session_state:
        st.session_state.quote = random.choice(QUOTES)
    return st.session_state.quote


def render(data, companies, sectors, profile, go_to):
    q_text, q_author = _quote()
    st.markdown(f'<div class="quote-banner">"{q_text}" &nbsp;— <strong>{q_author}</strong></div>', unsafe_allow_html=True)

    first_name_bit = "" if profile.get("investor_type") is None else f" - {profile['investor_type']} Investor"
    st.markdown(f"# Dashboard{first_name_bit}")
    st.caption("Your personal starting point for exploring the Colombo Stock Exchange.")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Companies Covered", data["meta"]["total_companies"])
    m2.metric("Brokers Profiled", data["meta"]["total_brokers"])
    m3.metric("Sectors Analysed", data["meta"]["total_sectors"])
    m4.metric("Data Coverage", data["meta"]["data_years"])

    st.divider()

    left, right = st.columns([1.4, 1])

    with left:
        st.markdown("### Your Portfolio at a Glance")
        portfolio = load_portfolio()
        if not portfolio:
            st.markdown("""
            <div class="section-card">
                <p style="color:#5a7199;font-size:0.9rem;">
                You haven't added any companies to your portfolio yet. Head to
                <strong>Discover Companies</strong> to find some worth watching.
                </p>
            </div>""", unsafe_allow_html=True)
            if st.button("Discover Companies →"):
                go_to("Discover Companies")
        else:
            rows_html = ""
            for name in portfolio[:5]:
                fd = companies.get(name, {})
                if not fd:
                    continue
                ai = compute_ai_recommendation(fd, investor_type=resolve_investor_type(fd))
                mp = latest(get_series(fd, "market_metrics", "market_price"))
                rows_html += f"""
                <div style="display:flex;justify-content:space-between;align-items:center;padding:10px 0;border-bottom:1px solid #EEF0FB;">
                    <div>
                        <div style="font-weight:700;color:#15172E;font-size:0.9rem;">{name}</div>
                        <div style="color:#8B93AD;font-size:0.75rem;">{fd.get('sector','—')}</div>
                    </div>
                    <div style="text-align:right;">
                        <div style="font-weight:700;color:#15172E;">{fmt(mp,'LKR ')}</div>
                        <div style="margin-top:4px;">{recommendation_pill(ai['recommendation'])}</div>
                    </div>
                </div>"""
            st.markdown(f'<div class="section-card">{rows_html}</div>', unsafe_allow_html=True)
            if st.button("Go to Portfolio →"):
                go_to("Portfolio")

    with right:
        st.markdown("### Quick Actions")
        st.markdown("""
        <div class="section-card">
            <p style="color:#5a7199;font-size:0.87rem;margin:0 0 10px 0;">New to the CSE? Start here.</p>
        </div>""", unsafe_allow_html=True)
        if st.button("Getting Started Guide", use_container_width=True):
            go_to("Getting Started")
        if st.button("Explore Market Dashboard", use_container_width=True):
            go_to("Market Dashboard")
        if st.button("Visit Learning Centre", use_container_width=True):
            go_to("Learning Centre")

    st.divider()

    if profile.get("wants_recommendations") == "Yes":
        st.markdown("### Recommended For You")
        st.caption("A quick starting shortlist based on Benjamin Graham scoring and your risk profile.")
        candidates = []
        sample_names = list(companies.keys())
        random.Random(7).shuffle(sample_names)  # stable order across reruns
        for name in sample_names[:40]:
            fd = companies[name]
            inv_type = resolve_investor_type(fd)
            total, _ = score_defensive(fd) if inv_type == "defensive" else score_enterprising(fd)
            if total >= 65:
                candidates.append((name, fd, total, inv_type))
            if len(candidates) >= 6:
                break

        if not candidates:
            st.info("Not enough scored companies yet to build a shortlist. Try Discover Companies instead.")
        else:
            cols = st.columns(3)
            for i, (name, fd, total, inv_type) in enumerate(candidates):
                ai = compute_ai_recommendation(fd, investor_type=inv_type)
                with cols[i % 3]:
                    st.markdown(f"""
                    <div class="section-card">
                        <div style="font-weight:700;color:#15172E;">{name}</div>
                        <div style="color:#8B93AD;font-size:0.75rem;margin-bottom:8px;">{fd.get('sector','—')}</div>
                        {recommendation_pill(ai['recommendation'])} {risk_pill(ai['risk_rating'])}
                    </div>""", unsafe_allow_html=True)
                    if st.button("View", key=f"dash_rec_{name}", use_container_width=True):
                        st.session_state.workspace_company = name
                        go_to("Company Workspace")
