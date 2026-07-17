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


# ── Personalized "Recommended For You" shortlist ────────────────────────────
# Every answer from onboarding that isn't purely cosmetic feeds into this:
#   - investor_type -> which Graham methodology is even eligible to appear
#     (Beginners only see Defensive-scored, well-established companies;
#     Intermediate/Experienced also see Enterprising-scored companies,
#     which by nature include smaller, higher-growth, higher-risk names).
#   - risk_appetite  -> the score threshold to clear, and the ceiling on
#     how much risk is allowed into the shortlist at all.
#   - investment_goal -> the sort order applied to whatever clears the bar
#     (dividend yield for income-seekers, EPS growth for growth-seekers,
#     overall score otherwise).
# Two users with different answers can and will see a different shortlist -
# this is not just relabeling the same fixed list.

def _risk_profile(risk_appetite):
    if risk_appetite == "Low":
        return 65, {"Low"}
    if risk_appetite == "High":
        return 45, {"Low", "Medium", "High"}
    return 55, {"Low", "Medium"}  # Medium / unanswered


def _select_recommendations(companies, profile, limit=6, pool_size=40):
    investor_type = profile.get("investor_type") or "Beginner"
    allow_enterprising = investor_type in ("Intermediate", "Experienced")
    min_score, allowed_risk = _risk_profile(profile.get("risk_appetite"))
    goal = profile.get("investment_goal")

    sample_names = list(companies.keys())
    random.Random(7).shuffle(sample_names)  # stable order across reruns

    candidates = []
    for name in sample_names:
        fd = companies[name]
        established = available_years(fd) >= 9
        if not established and not allow_enterprising:
            continue  # Beginners: stick to companies with a long, provable track record
        inv_type = "defensive" if established else "enterprising"
        total, _ = score_defensive(fd) if inv_type == "defensive" else score_enterprising(fd)
        if total is None or total < min_score:
            continue
        ai = compute_ai_recommendation(fd, investor_type=inv_type)
        if ai["risk_rating"] not in allowed_risk:
            continue
        candidates.append((name, fd, total, ai))
        if len(candidates) >= pool_size:
            break

    if goal == "Dividend Income":
        candidates.sort(key=lambda c: -(latest(get_series(c[1], "income_statement", "dividend_per_share")) or 0))
    elif goal in ("Long-term Growth", "Capital Appreciation"):
        def _avg_growth(fd):
            vals = [v for v in get_series(fd, "growth", "eps_growth_yoy").values() if isinstance(v, (int, float))]
            return sum(vals) / len(vals) if vals else -999
        candidates.sort(key=lambda c: -_avg_growth(c[1]))
    else:
        candidates.sort(key=lambda c: -c[2])

    return candidates[:limit]


def _recommendation_caption(profile):
    bits = []
    if profile.get("investor_type"):
        bits.append(f"{profile['investor_type'].lower()} investor")
    if profile.get("risk_appetite"):
        bits.append(f"{profile['risk_appetite'].lower()} risk appetite")
    if profile.get("investment_goal") and profile["investment_goal"] != "Undecided":
        bits.append(f"a focus on {profile['investment_goal'].lower()}")
    if not bits:
        return "A quick starting shortlist based on Benjamin Graham scoring."
    return "Tailored to your profile — " + ", ".join(bits) + "."

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
                total, _ = score_defensive(fd) if available_years(fd) >= 9 else (None, None)
                ai = compute_ai_recommendation(fd, investor_type="defensive" if total is not None else "enterprising")
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
            if available_years(fd) < 9:
                continue
            total, _ = score_defensive(fd)
            if total >= 65:
                candidates.append((name, fd, total))
            if len(candidates) >= 6:
                break

        if not candidates:
            st.info("Not enough scored companies yet to build a shortlist. Try Discover Companies instead.")
        else:
            cols = st.columns(3)
            for i, (name, fd, total) in enumerate(candidates):
                ai = compute_ai_recommendation(fd, investor_type="defensive")
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
