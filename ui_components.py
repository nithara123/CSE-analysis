"""
ui_components.py
-----------------
Reusable, presentation-only building blocks shared across the Discover
Companies, Company Workspace, Portfolio and Sector Analytics pages. None
of this touches calculations - it only renders values that are passed in.

Keeping these in one module means every "card" in the app looks and
behaves consistently, and a future design tweak only needs to happen in
one place.
"""

import streamlit as st


def small_metric(label, value, sub=None, sub_color="#5a7199"):
    sub_html = (f'<div style="font-size:0.68rem;color:{sub_color};margin-top:3px;line-height:1.2;">{sub}</div>'
                if sub else "")
    st.markdown(f"""
    <div style="background:white;padding:10px 8px;border-radius:10px;
                border:1px solid #e0e7ef;text-align:center;
                min-height:74px;box-sizing:border-box;
                display:flex;flex-direction:column;justify-content:center;
                overflow:hidden;">
        <div style="font-size:0.65rem;color:#5a7199;font-weight:600;line-height:1.2;">{label}</div>
        <div style="font-size:0.9rem;font-weight:700;color:#0B1D51;white-space:nowrap;line-height:1.3;margin-top:2px;">{value}</div>
        {sub_html}
    </div>
    """, unsafe_allow_html=True)


def recommendation_pill(recommendation):
    colors = {
        "Strong Buy": ("#DCFCF5", "#0F7A6C"),
        "Buy":        ("#DCFCF5", "#0F7A6C"),
        "Hold":       ("#FEF3D9", "#9A6B0C"),
        "Avoid":      ("#FFE4E1", "#C43D2E"),
        "Sell":       ("#FFE4E1", "#C43D2E"),
    }
    bg, fg = colors.get(recommendation, ("#EEF0FB", "#5a7199"))
    return f'<span style="background:{bg};color:{fg};padding:3px 12px;border-radius:999px;font-size:0.76rem;font-weight:700;">{recommendation}</span>'


def risk_pill(risk_rating):
    colors = {"Low": ("#DCFCF5", "#0F7A6C"), "Medium": ("#FEF3D9", "#9A6B0C"), "High": ("#FFE4E1", "#C43D2E")}
    bg, fg = colors.get(risk_rating, ("#EEF0FB", "#5a7199"))
    return f'<span style="background:{bg};color:{fg};padding:3px 12px;border-radius:999px;font-size:0.76rem;font-weight:700;">{risk_rating} Risk</span>'


def render_company_card(company_name, fd, ai_result, in_portfolio=False, key_prefix=""):
    """
    Company card for Discover Companies: name, sector, price, AI score,
    Graham result, news sentiment, risk, quick recommendation + actions.
    Returns which button (if any) was clicked this run: "view" | "add" | None.
    """
    from graham_engine import get_series, latest, fmt

    mp = latest(get_series(fd, "market_metrics", "market_price"))
    sector = fd.get("sector", "—")
    score = ai_result["score"]
    recommendation = ai_result["recommendation"]
    risk = ai_result["risk_rating"]
    graham_total = ai_result["graham_total"]

    news_comp = next((c for c in ai_result["components"] if c["key"] == "news"), None)
    news_label = "Not enough coverage"
    if news_comp and news_comp["score"] is not None:
        news_label = "Positive" if news_comp["score"] >= 60 else ("Negative" if news_comp["score"] <= 40 else "Neutral")

    st.markdown(f"""
    <div class="section-card" style="margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;">
            <div>
                <div style="font-weight:700;color:#15172E;font-size:1rem;font-family:'Sora',sans-serif;">{company_name}</div>
                <div style="color:#8B93AD;font-size:0.78rem;margin-top:2px;">{sector}</div>
            </div>
            <div style="text-align:right;">
                <div style="font-weight:800;font-size:1.3rem;color:#15172E;font-family:'Sora',sans-serif;">{fmt(mp, 'LKR ')}</div>
            </div>
        </div>
        <div style="display:flex;gap:8px;margin-top:12px;flex-wrap:wrap;">
            {recommendation_pill(recommendation)}
            {risk_pill(risk)}
        </div>
        <div style="display:flex;justify-content:space-between;margin-top:14px;font-size:0.8rem;color:#5a7199;">
            <div>AI Score: <strong style="color:#15172E;">{score:.0f}/100</strong></div>
            <div>Graham: <strong style="color:#15172E;">{graham_total}/100</strong></div>
            <div>News: <strong style="color:#15172E;">{news_label}</strong></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    b1, b2 = st.columns(2)
    action = None
    with b1:
        if st.button("View Details", key=f"{key_prefix}_view_{company_name}", use_container_width=True):
            action = "view"
    with b2:
        label = "In Portfolio ✓" if in_portfolio else "Add to Portfolio"
        if st.button(label, key=f"{key_prefix}_add_{company_name}", use_container_width=True,
                     disabled=in_portfolio):
            action = "add"
    return action


def render_score_card(score, label):
    if score >= 75:
        color, verdict = "#16a34a", "Strong - Meets Criteria"
    elif score >= 50:
        color, verdict = "#d97706", "Moderate - Partially Meets Criteria"
    else:
        color, verdict = "#dc2626", "Weak - Does Not Meet Criteria"
    st.markdown(f"""
    <div class="score-block">
        <div class="score-num" style="color:{color};">{score}</div>
        <div style="font-size:0.7rem; color:#94a3b8; margin-top:2px;">out of 100</div>
        <div class="score-label">{label}</div>
        <div class="score-verdict" style="color:{color};">{verdict}</div>
    </div>""", unsafe_allow_html=True)


def render_ai_score_card(ai_result):
    score = ai_result["score"]
    if score >= 65:
        color = "#16a34a"
    elif score >= 45:
        color = "#d97706"
    else:
        color = "#dc2626"
    st.markdown(f"""
    <div class="score-block">
        <div class="score-num" style="color:{color};">{score:.0f}</div>
        <div style="font-size:0.7rem; color:#94a3b8; margin-top:2px;">out of 100</div>
        <div class="score-label">AI Recommendation Score</div>
        <div class="score-verdict" style="color:{color};">{ai_result['recommendation']}</div>
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


def render_ai_components_breakdown(components):
    """Bar-style breakdown of what fed into the AI Recommendation Score."""
    for c in components:
        if c["score"] is None:
            st.markdown(f"""
            <div class="criteria-row">
                <div class="criteria-icon">⚪</div>
                <div style="flex:1;">
                    <div class="criteria-name">{c['name']}</div>
                    <div class="criteria-detail">Not available: {c['note']}</div>
                </div>
            </div>""", unsafe_allow_html=True)
            continue
        pct = c["score"]
        bar_color = "#16a34a" if pct >= 65 else ("#d97706" if pct >= 45 else "#dc2626")
        st.markdown(f"""
        <div class="criteria-row" style="display:block;">
            <div style="display:flex;justify-content:space-between;">
                <div class="criteria-name">{c['name']} <span style="color:#8B93AD;font-weight:500;">(weight {c['weight']*100:.0f}%)</span></div>
                <div class="criteria-pts" style="color:{bar_color};">{pct:.0f}/100</div>
            </div>
            <div style="background:#EEF0FB;border-radius:6px;height:8px;margin-top:6px;overflow:hidden;">
                <div style="background:{bar_color};width:{pct}%;height:100%;"></div>
            </div>
            <div class="criteria-detail" style="margin-top:4px;">{c['note']}</div>
        </div>""", unsafe_allow_html=True)


def render_comparison_snapshot(company_name, ai_result, fd, is_winner=False):
    """Snapshot card for the Company Comparison view (Portfolio > Compare)."""
    from graham_engine import get_series, latest, fmt
    financial_health = "Strong" if fd_debt_ok(fd) else "Moderate"
    growth = "N/A"
    growth_series = get_series(fd, "growth", "eps_growth_yoy")
    if growth_series:
        avg_g = sum(growth_series.values()) / len(growth_series)
        growth = f"{avg_g:+.1%}"

    border = "border:2px solid #14B8A6;" if is_winner else "border:1px solid #EAEDF7;"
    winner_badge = '<div style="position:absolute;top:-10px;right:14px;background:#14B8A6;color:white;font-size:0.68rem;font-weight:700;padding:3px 10px;border-radius:999px;">TOP PICK</div>' if is_winner else ""

    st.markdown(f"""
    <div class="section-card" style="{border}position:relative;">
        {winner_badge}
        <div style="font-weight:700;color:#15172E;font-size:1rem;font-family:'Sora',sans-serif;">{company_name}</div>
        <div style="color:#8B93AD;font-size:0.78rem;margin:2px 0 12px 0;">{fd.get('sector','—')}</div>
        <div style="display:flex;flex-direction:column;gap:8px;font-size:0.85rem;">
            <div style="display:flex;justify-content:space-between;"><span style="color:#8B93AD;">Overall Score</span><strong>{ai_result['score']:.0f}/100</strong></div>
            <div style="display:flex;justify-content:space-between;"><span style="color:#8B93AD;">Financial Health</span><strong>{financial_health}</strong></div>
            <div style="display:flex;justify-content:space-between;"><span style="color:#8B93AD;">Valuation</span><strong>{fmt(latest(get_series(fd,'graham_analysis','margin_of_safety')), suffix='', dec=2)}</strong></div>
            <div style="display:flex;justify-content:space-between;"><span style="color:#8B93AD;">Growth (EPS YoY)</span><strong>{growth}</strong></div>
            <div style="display:flex;justify-content:space-between;"><span style="color:#8B93AD;">Risk</span><strong>{ai_result['risk_rating']}</strong></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def fd_debt_ok(fd):
    from graham_engine import get_series, latest
    dr = latest(get_series(fd, "ratios", "debt_ratio"))
    return dr is not None and dr < 0.5
