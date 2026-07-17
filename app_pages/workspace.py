"""
pages/workspace.py
--------------------
Company Workspace: everything about ONE company lives here. This is the
most detailed page in the app, per the redesign brief - price movement,
AI recommendation + plain-English explanation, financial overview (each
metric with an explain-it-to-me button), full Benjamin Graham breakdown,
and a company-scoped news feed grouped by sentiment and document type.
"""

import streamlit as st

from graham_engine import (
    get_series, latest, fmt, fmt_large, available_years,
    score_defensive, score_enterprising,
)
from ai_engine import compute_ai_recommendation, natural_language_summary, compute_sector_average_graham
from ui_components import (
    recommendation_pill, risk_pill, small_metric, render_criteria,
    render_ai_score_card, render_ai_components_breakdown,
)
from metric_info import render_metric_info, METRICS
from investor_profile import resolve_investor_type, get_profile_choice, queue_profile_change
from portfolio_store import load_portfolio, add_company, remove_company
from cse_price_chart import render_price_movement_section, fetch_best_daily_price_history
from macro_signals import estimate_macro_outlook
from news_intelligence import (
    SRI_LANKA_FEEDS, GLOBAL_FEEDS, fetch_region, detect_companies,
    detect_sectors, score_sentiment, time_ago,
)

# Which Graham criterion name maps to which metric_info entry, so the
# "Expand" panel under Benjamin Graham can show a Definition/Formula pulled
# from the same shared library used in Financial Overview - one source of
# truth, no duplicated wording.
CRITERION_METRIC_MAP = {
    "Earnings Consistency (10 Years)": "eps",
    "Earnings Stability (5 Years)": "eps",
    "Dividend History (10 Years)": "dividend",
    "Dividend Record (5 Years)": "dividend",
    "Financial Health — Current Ratio >= 2.0": "current_ratio",
    "Financial Strength": "current_ratio",
    "Low Debt (Debt Ratio < 0.5)": "debt_ratio",
    "Valuation Limits (P/E <= 20 latest, <= 25 on 7yr avg)": "pe_ratio",
    "Valuation (P/E <= 15, P/B <= 1.5)": "pe_ratio",
    "Margin of Safety >= 33%": "margin_of_safety",
    "Company Quality (Positive Book Value & Revenue)": "book_value",
    "Earnings Growth (5 Years)": "eps",
}

# Keyword -> document-type bucket for the company news feed.
DOC_TYPE_KEYWORDS = {
    "Quarterly Reports": ["quarterly", "q1", "q2", "q3", "q4", "interim results", "interim financial"],
    "Annual Reports": ["annual report", "full year results", "fy20", "annual general meeting", "agm"],
    "Dividend Announcements": ["dividend", "interim dividend", "final dividend"],
    "Rights Issues": ["rights issue", "rights offer"],
    "CSE Notifications": ["cse notice", "colombo stock exchange notice", "trading halt", "circular"],
    "Director Changes": ["appointment of director", "resignation of director", "board change", "director change"],
    "Acquisitions": ["acquisition", "acquire", "merger", "stake purchase", "divest"],
    "Press Releases": [],  # fallback bucket
}


def _classify_doc_type(text):
    text_l = text.lower()
    for bucket, kws in DOC_TYPE_KEYWORDS.items():
        if any(kw in text_l for kw in kws):
            return bucket
    return "Press Releases"


def _all_news_items():
    return fetch_region(tuple(SRI_LANKA_FEEDS.items())) + fetch_region(tuple(GLOBAL_FEEDS.items()))


def _company_news(company_name, fd, companies, items):
    single = {company_name: fd}
    matched = []
    for item in items:
        text = f"{item['title']} {item['summary']}"
        if company_name in detect_companies(text, single):
            matched.append(item)
    return matched


def _sector_news(sector_name, items):
    """Articles that mention this company's sector generally, even when no
    article names the company directly. Kept as a SEPARATE, clearly-labelled
    section rather than folded into the company's own News tab or into the
    AI engine's news_sentiment_counts - sector chatter isn't the same signal
    as coverage of the company itself, and treating it as such would
    overstate how much is actually known about this specific company."""
    if not sector_name:
        return []
    matched = []
    for item in items:
        text = f"{item['title']} {item['summary']}"
        if sector_name in detect_sectors(text):
            matched.append(item)
    return matched


@st.cache_data(show_spinner=False)
def _cached_sector_avg_score(sector_name, investor_type, _companies, _sectors):
    peer_names = _sectors.get(sector_name, {}).get("companies", [])
    return compute_sector_average_graham(peer_names, _companies, investor_type)


def render(data, companies, sectors, profile, go_to):
    all_names = sorted(companies.keys())

    preselected = st.session_state.get("workspace_company")
    default_idx = all_names.index(preselected) + 1 if preselected in all_names else 0

    company_name = st.selectbox("Select a company", ["— Select —"] + all_names, index=default_idx)
    if company_name == "— Select —":
        st.info("Select a company above to open its Workspace.")
        return
    st.session_state.workspace_company = company_name

    fd = companies.get(company_name, {})
    if not fd:
        st.error("No data found for this company.")
        return

    investor_type = resolve_investor_type(fd)
    if investor_type == "defensive":
        graham_total, criteria = score_defensive(fd)
    else:
        graham_total, criteria = score_enterprising(fd)

    # ── news pool, fetched once per session-load (cached inside fetch_region) ──
    with st.spinner("Checking recent news..."):
        all_items = _all_news_items()
        news_items = _company_news(company_name, fd, companies, all_items)
        sector_news_items = _sector_news(fd.get("sector"), all_items)

    pos = neu = neg = 0
    for it in news_items:
        label, _, _ = score_sentiment(f"{it['title']} {it['summary']}")
        if label == "Positive":
            pos += 1
        elif label == "Negative":
            neg += 1
        else:
            neu += 1
    # Only genuine company-specific mentions feed the AI score's news signal
    # (see _sector_news docstring for why sector chatter is kept separate).
    news_counts = {"positive": pos, "neutral": neu, "negative": neg} if news_items else None

    # ── price history -> trend + volatility signals ────────────────────────
    with st.spinner("Loading price history..."):
        price_df = fetch_best_daily_price_history(fd.get("symbol"))
    price_series = price_df["Close"].dropna().tolist() if not price_df.empty else None

    # ── sector benchmark (average Graham score across sector peers) ────────
    sector_avg_score = _cached_sector_avg_score(fd.get("sector"), investor_type, companies, sectors)

    # ── macro backdrop (see macro_signals.py for what this is/isn't) ───────
    macro_outlook = estimate_macro_outlook()

    ai_result = compute_ai_recommendation(
        fd, investor_type=investor_type,
        news_sentiment_counts=news_counts,
        price_series=price_series,
        sector_avg_score=sector_avg_score,
        macro_outlook=macro_outlook,
    )

    mp = latest(get_series(fd, "market_metrics", "market_price"))
    mp_series = get_series(fd, "market_metrics", "market_price")
    prev_year_mp = None
    if len(mp_series) > 1:
        years_sorted = sorted(mp_series.keys())
        prev_year_mp = mp_series[years_sorted[-2]]
    change_str = "N/A"
    if mp is not None and prev_year_mp:
        pct = (mp - prev_year_mp) / prev_year_mp
        change_str = f"{pct:+.1%} (YoY)"

    # ── Top section ──────────────────────────────────────────────────────────
    portfolio = set(load_portfolio())
    in_portfolio = company_name in portfolio

    st.markdown(f"""
    <div class="company-header">
        <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:10px;">
            <div>
                <div style="font-size:1.3rem; font-weight:800;">{company_name} &nbsp;({fd.get('symbol','—')})</div>
                <div style="color:#90b8e0; font-size:0.85rem; margin-top:4px;">
                    {fd.get('sector','—')} &nbsp;|&nbsp; {fd.get('industry','—')}
                </div>
            </div>
            <div style="text-align:right;">
                <div style="font-size:1.4rem;font-weight:800;">{fmt(mp,'LKR ')}</div>
                <div style="color:#90b8e0;font-size:0.8rem;">{change_str}</div>
            </div>
        </div>
        <div style="margin-top:14px;display:flex;gap:8px;flex-wrap:wrap;">
            {recommendation_pill(ai_result['recommendation'])}
            {risk_pill(ai_result['risk_rating'])}
        </div>
    </div>""", unsafe_allow_html=True)

    # ── Defensive / Enterprising switch ─────────────────────────────────────
    # Lets you flip between Graham's two methodologies right here, without
    # digging into the sidebar. This changes the SAME global choice the
    # sidebar's "Investor Profile" control uses, so it applies everywhere
    # else in the app too (Discover, Portfolio, Dashboard, Market Dashboard) -
    # not just on this one company's page.
    global_choice = get_profile_choice()
    effective = "Defensive" if investor_type == "defensive" else "Enterprising"
    st.write("")
    st.markdown("**View this company as a...**")
    bcol1, bcol2 = st.columns(2)
    with bcol1:
        if st.button("Defensive Investor", key="workspace_pick_defensive", use_container_width=True,
                     type="primary" if effective == "Defensive" else "secondary"):
            queue_profile_change("Defensive")
    with bcol2:
        if st.button("Enterprising Investor", key="workspace_pick_enterprising", use_container_width=True,
                     type="primary" if effective == "Enterprising" else "secondary"):
            queue_profile_change("Enterprising")
    if global_choice == "Auto":
        st.caption(f"Currently on **Auto** — {company_name} has {available_years(fd)} year(s) of data on file, "
                    f"so it's being scored as a **{effective} Investor** for now. Pick a button above to lock "
                    "one methodology in everywhere in the app, or change it anytime from the sidebar.")
    else:
        st.caption("This choice applies app-wide - change it anytime from here or the sidebar.")

    if st.button("Remove from Portfolio" if in_portfolio else "Add to Portfolio"):
        if in_portfolio:
            remove_company(company_name)
        else:
            add_company(company_name)
        st.rerun()

    # ── Natural language explanation ─────────────────────────────────────────
    summary = natural_language_summary(fd, ai_result, company_name)
    st.markdown(f"""
    <div class="section-card" style="border-left:4px solid #4F46E5;">
        <p style="color:#15172E;font-size:0.95rem;line-height:1.6;margin:0;">{summary}</p>
    </div>""", unsafe_allow_html=True)

    st.write("")
    render_price_movement_section(fd.get("symbol"), company_name)

    st.divider()

    # ── AI Recommendation Score ──────────────────────────────────────────────
    st.markdown("### AI Recommendation")
    sc_col, br_col = st.columns([1, 2])
    with sc_col:
        render_ai_score_card(ai_result)
    with br_col:
        st.markdown("**What this score is based on**")
        render_ai_components_breakdown(ai_result["components"])

    st.divider()

    # ── Financial Overview ───────────────────────────────────────────────────
    st.markdown("### Financial Overview")
    st.caption("Every number below has an ℹ️ button explaining what it means, how it's calculated, and why it matters.")

    eps_v = latest(get_series(fd, "income_statement", "eps"))
    rev_v = latest(get_series(fd, "income_statement", "total_revenue"))
    div_v = latest(get_series(fd, "income_statement", "dividend_per_share"))
    cr_v = latest(get_series(fd, "ratios", "current_ratio"))
    dr_v = latest(get_series(fd, "ratios", "debt_ratio"))
    bv_v = latest(get_series(fd, "market_metrics", "bvps"))
    iv_v = latest(get_series(fd, "graham_analysis", "intrinsic_value"))
    mos_v = latest(get_series(fd, "graham_analysis", "margin_of_safety"))

    metric_rows = [
        ("EPS", fmt(eps_v, "LKR "), "eps"),
        ("Revenue", fmt_large(rev_v), "revenue"),
        ("Dividend", fmt(div_v, "LKR "), "dividend"),
        ("Current Ratio", fmt(cr_v), "current_ratio"),
        ("Debt Ratio", fmt(dr_v), "debt_ratio"),
        ("Book Value", fmt(bv_v, "LKR "), "book_value"),
        ("Intrinsic Value", fmt(iv_v, "LKR "), "intrinsic_value"),
        ("Margin of Safety", f"{mos_v:.1%}" if mos_v is not None else "N/A", "margin_of_safety"),
    ]
    for row_start in range(0, len(metric_rows), 4):
        cols = st.columns(4)
        for col, (label, value, mkey) in zip(cols, metric_rows[row_start:row_start + 4]):
            with col:
                small_metric(label, value)
                render_metric_info(mkey, st)

    st.divider()

    # ── Benjamin Graham ───────────────────────────────────────────────────────
    label = "Defensive Investor" if investor_type == "defensive" else "Enterprising Investor"
    st.markdown(f"### Benjamin Graham Analysis — {label}")
    passed = sum(1 for c in criteria if c["met"])
    st.markdown(f"**Overall score: {graham_total}/100** &nbsp;|&nbsp; **{passed}/{len(criteria)} criteria passed**")

    for c in criteria:
        icon = "✅" if c["met"] else "❌"
        with st.expander(f"{icon} {c['name']} — {c['pts']}/{c['max']} pts"):
            mkey = CRITERION_METRIC_MAP.get(c["name"])
            if mkey:
                info = METRICS.get(mkey)
                if info:
                    st.markdown(f"*Definition:* {info['definition']}")
                    st.code(info["formula"], language="text")
            st.markdown(f"*Reason:* {c['detail']}")
            st.markdown(f"*Interpretation:* {c['desc']}")

    st.divider()

    # ── News ──────────────────────────────────────────────────────────────────
    st.markdown("### News")
    if not news_items:
        st.info("No recent news mentioning this company by name was found in the connected feeds. "
                 "Check the **Sector News** tab below for broader coverage of "
                 f"{fd.get('sector', 'this sector')} that may still be relevant.")
    else:
        n_pos = [i for i in news_items if score_sentiment(f"{i['title']} {i['summary']}")[0] == "Positive"]
        n_neu = [i for i in news_items if score_sentiment(f"{i['title']} {i['summary']}")[0] == "Neutral"]
        n_neg = [i for i in news_items if score_sentiment(f"{i['title']} {i['summary']}")[0] == "Negative"]

        tabs = st.tabs([f"Positive ({len(n_pos)})", f"Neutral ({len(n_neu)})", f"Negative ({len(n_neg)})", "By Document Type"])
        for tab, group in zip(tabs[:3], [n_pos, n_neu, n_neg]):
            with tab:
                if not group:
                    st.caption("No articles in this category.")
                for item in group[:15]:
                    _render_news_row(item)

        with tabs[3]:
            buckets = {k: [] for k in DOC_TYPE_KEYWORDS}
            for item in news_items:
                bucket = _classify_doc_type(f"{item['title']} {item['summary']}")
                buckets[bucket].append(item)
            for bucket, items in buckets.items():
                if items:
                    st.markdown(f"**{bucket}** ({len(items)})")
                    for item in items[:10]:
                        _render_news_row(item)

    st.markdown("#### Sector News")
    st.caption(f"Broader coverage mentioning the {fd.get('sector', '—')} sector generally - useful context, "
               "but not necessarily about this company specifically.")
    if not sector_news_items:
        st.caption("No recent sector-level articles found in the connected feeds either.")
    else:
        for item in sector_news_items[:10]:
            _render_news_row(item)


def _render_news_row(item):
    st.markdown(f"""
    <div style="background:#ffffff;border:1px solid #e0e7ef;border-radius:12px;
                padding:12px 16px;margin-bottom:8px;">
        <a href="{item['link']}" target="_blank" style="color:#15172E;font-weight:700;font-size:0.88rem;text-decoration:none;">{item['title']}</a>
        <div style="font-size:0.72rem;color:#8B93AD;margin-top:4px;">{item['source']} &nbsp;•&nbsp; {time_ago(item['published'])}</div>
    </div>""", unsafe_allow_html=True)
