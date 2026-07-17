"""
pages/portfolio.py
--------------------
Portfolio / Watchlist: add, remove, compare, and analyse. "Compare" uses
snapshot cards (never a giant table) and explicitly names a winner with a
reason, per the redesign brief.
"""

import streamlit as st
import plotly.graph_objects as go

from graham_engine import get_series, latest, fmt, available_years, score_defensive, score_enterprising
from ai_engine import compute_ai_recommendation
from ui_components import recommendation_pill, risk_pill, render_comparison_snapshot
from portfolio_store import load_portfolio, add_company, remove_company
from investor_profile import resolve_investor_type


def _ai_for(fd):
    inv_type = resolve_investor_type(fd)
    return inv_type, compute_ai_recommendation(fd, investor_type=inv_type)


def render(data, companies, sectors, profile, go_to):
    st.markdown("## Portfolio")
    st.caption("Your personal watchlist of companies to track and compare.")

    portfolio = load_portfolio()

    with st.expander("+ Add a company to your portfolio"):
        all_names = sorted(companies.keys())
        remaining = [n for n in all_names if n not in portfolio]
        pick = st.selectbox("Company", ["— Select —"] + remaining, key="port_add_pick")
        if pick != "— Select —" and st.button("Add", key="port_add_btn"):
            add_company(pick)
            st.rerun()

    if not portfolio:
        st.info("Your portfolio is empty. Add companies from here or from Discover Companies.")
        return

    st.divider()
    st.markdown("### Holdings")

    rows_data = []
    for name in portfolio:
        fd = companies.get(name, {})
        if not fd:
            continue
        inv_type, ai = _ai_for(fd)
        rows_data.append((name, fd, inv_type, ai))

    for name, fd, inv_type, ai in rows_data:
        mp = latest(get_series(fd, "market_metrics", "market_price"))
        defensive_total, _ = score_defensive(fd)
        enterprising_total, _ = score_enterprising(fd)
        c1, c2, c3, c4, c5, c6 = st.columns([2, 1, 1, 1, 1, 1])
        c1.markdown(f"**{name}**  \n<span style='color:#8B93AD;font-size:0.78rem;'>{fd.get('sector','—')}</span>", unsafe_allow_html=True)
        c2.markdown(fmt(mp, "LKR "))
        c3.markdown(f"Defensive {defensive_total}/100")
        c4.markdown(f"Enterprising {enterprising_total}/100")
        c5.markdown(recommendation_pill(ai["recommendation"]), unsafe_allow_html=True)
        c5.caption(f"as {'Defensive' if inv_type == 'defensive' else 'Enterprising'} Investor")
        with c6:
            b1, b2 = st.columns(2)
            with b1:
                if st.button("View", key=f"port_view_{name}"):
                    st.session_state.workspace_company = name
                    go_to("Company Workspace")
            with b2:
                if st.button("✕", key=f"port_rm_{name}"):
                    remove_company(name)
                    st.rerun()
        st.markdown("<hr style='margin:6px 0;border-color:#EEF0FB;'>", unsafe_allow_html=True)

    st.divider()

    # ── Compare ───────────────────────────────────────────────────────────────
    st.markdown("### Compare Companies")
    compare_selection = st.multiselect(
        "Choose 2-4 holdings to compare", [n for n, *_ in rows_data],
        max_selections=4, key="port_compare_pick",
    )
    if len(compare_selection) >= 2:
        compared = [(n, fd, ai) for n, fd, it, ai in rows_data if n in compare_selection]
        winner_name = max(compared, key=lambda t: t[2]["score"])[0]

        cols = st.columns(len(compared))
        for col, (name, fd, ai) in zip(cols, compared):
            with col:
                try:
                    render_comparison_snapshot(name, ai, fd, is_winner=(name == winner_name))
                except Exception as e:
                    st.error(f"Couldn't build a comparison card for **{name}** ({e}). "
                             "The other companies below are unaffected.")

        winner_ai = next(ai for n, fd, ai in compared if n == winner_name)
        st.markdown(f"""
        <div class="section-card" style="border-left:4px solid #14B8A6;">
            <strong>{winner_name}</strong> comes out ahead here, mainly because {winner_ai['explanation'].split('. ', 1)[-1]}
        </div>""", unsafe_allow_html=True)
    elif compare_selection:
        st.info("Pick at least 2 companies to compare.")

    st.divider()

    # ── Analyse Portfolio ────────────────────────────────────────────────────
    st.markdown("### Analyse Portfolio")
    if len(rows_data) >= 1:
        avg_score = sum(ai["score"] for *_, ai in rows_data) / len(rows_data)
        risk_counts = {"Low": 0, "Medium": 0, "High": 0}
        sector_counts = {}
        for name, fd, inv_type, ai in rows_data:
            risk_counts[ai["risk_rating"]] += 1
            sec = fd.get("sector", "Unknown")
            sector_counts[sec] = sector_counts.get(sec, 0) + 1

        m1, m2, m3 = st.columns(3)
        m1.metric("Average AI Score", f"{avg_score:.0f}/100")
        m2.metric("Holdings", len(rows_data))
        dominant_risk = max(risk_counts, key=risk_counts.get)
        m3.metric("Dominant Risk Level", dominant_risk)

        fig = go.Figure(go.Pie(labels=list(sector_counts.keys()), values=list(sector_counts.values()), hole=0.5))
        fig.update_layout(title=dict(text="Sector Concentration", font=dict(color="#15172E", size=13), x=0),
                           paper_bgcolor="#ffffff", height=320, margin=dict(l=10, r=10, t=40, b=10))
        st.plotly_chart(fig, use_container_width=True)

        if len(sector_counts) == 1:
            st.warning("Your entire portfolio sits in a single sector - consider diversifying across "
                       "sectors to reduce concentration risk.")
        elif max(sector_counts.values()) / len(rows_data) > 0.6:
            st.warning("More than 60% of your portfolio is concentrated in one sector - worth reviewing "
                       "your diversification.")
        else:
            st.success("Your portfolio is reasonably diversified across sectors.")
