"""
pages/learning_centre.py
--------------------------
Educational deep-dives, pulling from the same metric_info library used
inline in the Company Workspace, plus the Graham criteria explanations
carried over unchanged from the original Educational Portal.
"""

import streamlit as st

from metric_info import METRICS

CRITERIA_DEFENSIVE = [
    ("Earnings Consistency", "20 pts", "Positive EPS for all of the last 10 years with no deficits."),
    ("Dividend History", "15 pts", "Uninterrupted dividend payments for at least 10 years."),
    ("Financial Health — Current Ratio >= 2.0", "15 pts", "Current ratio of at least 2.0 to ensure strong short-term liquidity."),
    ("Low Debt — Debt Ratio < 0.5", "10 pts", "Low debt-to-asset ratio to ensure financial stability during downturns."),
    ("Valuation Limits (P/E)", "15 pts", "Not more than 20x last 12-month earnings or 25x 7-year average earnings."),
    ("Margin of Safety >= 33%", "15 pts", "Buy at a price significantly below intrinsic value to protect against error and market swings."),
    ("Company Quality", "10 pts", "Positive book value and consistent positive revenue — large, established company."),
]

CRITERIA_ENTERPRISING = [
    ("Financial Strength", "25 pts", "Current ratio > 1.5 and long-term debt < 110% of working capital."),
    ("Earnings Stability", "20 pts", "Positive EPS for each of the last 5 years."),
    ("Dividend Record", "15 pts", "Company pays some level of dividends — signals shareholder-friendly management."),
    ("Valuation (P/E <= 15, P/B <= 1.5)", "25 pts", "P/E below 10–15 and P/B below 1.2–1.5 to signal undervaluation."),
    ("Earnings Growth", "15 pts", "Demonstrated EPS growth over the past 5 years."),
]

# Example figures for the "Examples" part of each Learning Centre topic -
# illustrative only, not live company data.
EXAMPLES = {
    "eps": "A company with LKR 500M net profit and 100M shares outstanding has an EPS of LKR 5.00.",
    "revenue": "A company reporting LKR 2B in total revenue this year, up from LKR 1.8B last year, grew revenue ~11%.",
    "dividend": "A company paying LKR 2.50 per share annually, on a LKR 50 share price, yields 5%.",
    "current_ratio": "Current assets of LKR 300M against current liabilities of LKR 120M gives a current ratio of 2.5 — comfortably above Graham's 2.0 defensive threshold.",
    "debt_ratio": "Total debt of LKR 400M against total assets of LKR 1B gives a debt ratio of 0.4 — conservative leverage.",
    "book_value": "Net assets of LKR 800M across 50M shares gives a book value of LKR 16.00 per share.",
    "intrinsic_value": "EPS of LKR 8 and BVPS of LKR 40 gives an intrinsic value of √(22.5 × 8 × 40) ≈ LKR 84.85.",
    "margin_of_safety": "If intrinsic value is LKR 85 and the market price is LKR 55, the margin of safety is (85-55)/85 ≈ 35%.",
    "pe_ratio": "A share priced at LKR 100 with EPS of LKR 8 has a P/E of 12.5x.",
    "pb_ratio": "A share priced at LKR 60 with a book value of LKR 40 has a P/B of 1.5x.",
}


def render(data, companies, sectors, profile):
    st.markdown("## Learning Centre")
    st.caption("Understand the key metrics and methodology behind Graham-style value investing.")

    tab1, tab2, tab3 = st.tabs(["Key Metrics Explained", "Defensive Investor Criteria", "Enterprising Investor Criteria"])

    with tab1:
        for key, info in METRICS.items():
            with st.expander(info["label"]):
                l, r = st.columns([3, 1])
                with l:
                    st.markdown(f"**Definition:** {info['definition']}")
                    st.code(info["formula"], language="text")
                    st.markdown(f"**Interpretation:** {info['interpretation']}")
                    st.markdown(f"**Why it matters:** {info['why_it_matters']}")
                    example = EXAMPLES.get(key)
                    if example:
                        st.info(f"**Example:** {example}")
                with r:
                    st.caption("Used in:")
                    st.markdown("- Company Workspace\n- Benjamin Graham scoring")

    with tab2:
        st.markdown("### Defensive Investor — 7 Criteria (100 Points Total)")
        st.caption("Uses 10 years of data. Suited for risk-averse, long-term investors.")
        _render_criteria_list(CRITERIA_DEFENSIVE)

    with tab3:
        st.markdown("### Enterprising Investor — 5 Criteria (100 Points Total)")
        st.caption("Uses 5 years of data. Suited for active investors willing to take calculated risks.")
        _render_criteria_list(CRITERIA_ENTERPRISING)


def _render_criteria_list(criteria):
    for name, pts, desc in criteria:
        st.markdown(f"""
        <div style="display:flex;align-items:flex-start;gap:14px;padding:10px 0;border-bottom:1px solid #EEF0FB;">
            <div style="flex:1;">
                <span style="font-weight:700;color:#15172E;font-size:0.9rem;">{name}</span>
                <span style="color:#5a7199;font-size:0.82rem;"> — {desc}</span>
            </div>
            <div style="color:#4F46E5;font-weight:700;font-size:0.85rem;white-space:nowrap;">{pts}</div>
        </div>""", unsafe_allow_html=True)
