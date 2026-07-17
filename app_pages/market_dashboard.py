"""
pages/market_dashboard.py
---------------------------
Market-wide context: latest CSE-relevant announcements & news (reusing
news_intelligence.py unchanged), Sri Lankan macroeconomic indicators
(also unchanged - the World Bank-backed macro dashboard), and Sector
Profiles (an upgrade from a flat averages table to a per-sector profile
card: top companies, average scores, recent news, outlook).
"""

import streamlit as st
import plotly.graph_objects as go

from graham_engine import get_series, latest, score_defensive, score_enterprising, available_years
from ai_engine import compute_ai_recommendation
from investor_profile import resolve_investor_type
from macro_signals import fetch_live_usd_lkr
from news_intelligence import render_market_intelligence


def render(data, companies, sectors, profile):
    st.markdown("## Market Dashboard")
    st.caption("Market-wide announcements, Sri Lankan macroeconomic indicators, and sector-level context.")

    _render_live_fx_strip()

    tab_news, tab_sectors = st.tabs(["Announcements & Macro & Rates", "Sector Profiles"])

    with tab_news:
        render_market_intelligence(companies)

    with tab_sectors:
        _render_sector_profiles(companies, sectors)


def _render_live_fx_strip():
    rate, as_of = fetch_live_usd_lkr()
    if rate is None:
        return
    st.markdown(f"""
    <div class="section-card" style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:10px;padding:14px 22px;margin-bottom:16px;">
        <div>
            <span style="font-weight:800;color:#15172E;font-size:1.1rem;">USD/LKR: {rate:,.2f}</span>
            <span style="color:#8B93AD;font-size:0.78rem;margin-left:10px;">live market rate, updates every 30 min</span>
        </div>
        <div style="color:#8B93AD;font-size:0.72rem;">
            Not CBSL's official indicative rate (CBSL doesn't publish a public API) - for that,
            see <a href="https://www.cbsl.gov.lk/en/rates-and-indicators/exchange-rates" target="_blank">cbsl.gov.lk</a> directly.
        </div>
    </div>""", unsafe_allow_html=True)


def _render_sector_profiles(companies, sectors):
    sector_names = sorted(sectors.keys())
    chosen = st.selectbox("Choose a sector", sector_names)
    sec_info = sectors.get(chosen, {})
    sec_companies = sec_info.get("companies", [])

    scored = []
    for name in sec_companies:
        fd = companies.get(name, {})
        if not fd:
            continue
        inv_type = resolve_investor_type(fd)
        total, _ = score_defensive(fd) if inv_type == "defensive" else score_enterprising(fd)
        ai = compute_ai_recommendation(fd, investor_type=inv_type)
        scored.append((name, fd, total, ai))

    if not scored:
        st.info("No scored companies available for this sector yet.")
        return

    avg_ai = sum(a["score"] for *_, a in scored) / len(scored)
    avg_graham = sum(t for _, _, t, _ in scored) / len(scored)

    m1, m2, m3 = st.columns(3)
    m1.metric("Companies in Sector", len(scored))
    m2.metric("Avg AI Score", f"{avg_ai:.0f}/100")
    m3.metric("Avg Graham Score", f"{avg_graham:.0f}/100")

    if avg_ai >= 65:
        outlook, outlook_color = "Positive", "#16a34a"
    elif avg_ai >= 45:
        outlook, outlook_color = "Neutral", "#d97706"
    else:
        outlook, outlook_color = "Cautious", "#dc2626"

    risk_counts = {"Low": 0, "Medium": 0, "High": 0}
    for *_, ai in scored:
        risk_counts[ai["risk_rating"]] += 1
    dominant_risk = max(risk_counts, key=risk_counts.get)

    st.markdown(f"""
    <div class="section-card">
        <h3>{chosen} — Sector Outlook</h3>
        <p style="color:#5a7199;font-size:0.9rem;">
        Based on the average AI Recommendation Score across {len(scored)} companies, the outlook for this
        sector currently reads as <strong style="color:{outlook_color};">{outlook}</strong>, with a
        dominant risk profile of <strong>{dominant_risk}</strong>.
        </p>
    </div>""", unsafe_allow_html=True)

    st.markdown("#### Top Companies")
    top = sorted(scored, key=lambda t: t[3]["score"], reverse=True)[:5]
    cols = st.columns(len(top))
    for col, (name, fd, total, ai) in zip(cols, top):
        with col:
            st.markdown(f"""
            <div class="section-card" style="text-align:center;">
                <div style="font-weight:700;color:#15172E;font-size:0.88rem;">{name}</div>
                <div style="margin-top:8px;font-size:1.3rem;font-weight:800;color:#15172E;">{ai['score']:.0f}</div>
                <div style="color:#8B93AD;font-size:0.72rem;">AI Score</div>
            </div>""", unsafe_allow_html=True)

    st.markdown("#### Growth Trend (Average Revenue Growth)")
    growth_vals = []
    for name, fd, *_ in scored:
        g = latest(get_series(fd, "growth", "revenue_growth_yoy"))
        if g is not None:
            growth_vals.append(g)
    if growth_vals:
        avg_growth = sum(growth_vals) / len(growth_vals)
        fig = go.Figure(go.Indicator(
            mode="number+delta", value=avg_growth * 100,
            number={"suffix": "%", "font": {"color": "#15172E"}},
            delta={"reference": 0, "relative": False},
        ))
        fig.update_layout(height=180, paper_bgcolor="#ffffff", margin=dict(l=10, r=10, t=10, b=10))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.caption("Revenue growth data not available for this sector.")

    st.caption("For sector-specific news, use the Announcements & Macro tab and filter by this sector's keywords.")
