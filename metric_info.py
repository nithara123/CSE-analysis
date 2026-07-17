"""
metric_info.py
---------------
Central library of "what does this number mean" explanations, shared by
the Company Workspace's Financial Overview, the Benjamin Graham section,
and the Learning Centre - one definition per metric, used everywhere so
the wording never drifts between pages.

Every entry has: definition, formula, interpretation, why_it_matters.
"""

METRICS = {
    "eps": {
        "label": "EPS (Earnings Per Share)",
        "definition": "The portion of a company's profit allocated to each outstanding share.",
        "formula": "EPS = Net Profit / Shares Outstanding",
        "interpretation": "Higher and steadily growing EPS over time signals a healthier, more "
                           "profitable business. A single year's EPS matters less than the trend "
                           "across many years.",
        "why_it_matters": "It's the foundation of most valuation metrics (P/E, intrinsic value) and "
                           "the clearest single number for 'is this company actually making money?'",
    },
    "revenue": {
        "label": "Revenue",
        "definition": "Total income generated from the company's core business activities, before costs.",
        "formula": "Revenue = Total Sales (Goods/Services) for the period",
        "interpretation": "Consistent revenue growth suggests a business that is expanding demand for "
                           "its products or services. Flat or declining revenue is a caution flag even "
                           "if profit looks fine, since profit can be propped up by cost-cutting alone.",
        "why_it_matters": "It shows the size and growth trajectory of the underlying business, "
                           "independent of accounting choices that affect profit.",
    },
    "dividend": {
        "label": "Dividend Per Share",
        "definition": "Cash paid out to shareholders for each share they own, usually from profits.",
        "formula": "Dividend Per Share = Total Dividends Paid / Shares Outstanding",
        "interpretation": "A long, uninterrupted history of dividend payments (Graham looked for 10+ "
                           "years) suggests a stable, shareholder-friendly, cash-generative business.",
        "why_it_matters": "Dividends are a direct, tangible return on your investment rather than a "
                           "paper gain, and a cut dividend is often an early warning sign of trouble.",
    },
    "current_ratio": {
        "label": "Current Ratio",
        "definition": "A measure of a company's ability to pay its short-term (within one year) "
                       "obligations using its short-term assets.",
        "formula": "Current Ratio = Current Assets / Current Liabilities",
        "interpretation": "Above 2.0 is considered strong by Graham's defensive standard, 1.5 is the "
                           "more lenient enterprising standard, and below 1.0 means the company may "
                           "struggle to pay bills due within a year.",
        "why_it_matters": "It's an early-warning liquidity check - a profitable company can still get "
                           "into trouble if it can't cover near-term obligations.",
    },
    "debt_ratio": {
        "label": "Debt Ratio",
        "definition": "The proportion of a company's total assets that are financed by debt rather "
                       "than equity.",
        "formula": "Debt Ratio = Total Debt / Total Assets",
        "interpretation": "Below 0.5 is conservative and preferred by Graham. Above 0.65 signals "
                           "meaningful leverage, which amplifies both gains and losses and adds "
                           "repayment risk, especially if interest rates rise.",
        "why_it_matters": "Highly leveraged companies are more vulnerable during downturns, since debt "
                           "payments don't shrink even when profits do.",
    },
    "book_value": {
        "label": "Book Value Per Share (BVPS)",
        "definition": "The net asset value of the company attributable to each share, if it were "
                       "liquidated today.",
        "formula": "BVPS = (Total Assets − Intangible Assets − Total Liabilities) / Shares Outstanding",
        "interpretation": "Comparing the market price to BVPS (the Price-to-Book, or P/B, ratio) shows "
                           "whether the market is pricing the stock above or below its accounting net "
                           "worth. Graham preferred P/B under 1.5.",
        "why_it_matters": "It's a floor-value reference point, especially useful for asset-heavy "
                           "businesses like banks, finance companies and manufacturers.",
    },
    "intrinsic_value": {
        "label": "Intrinsic Value",
        "definition": "Benjamin Graham's estimate of what a share is really worth, based on its "
                       "earnings and book value, independent of its current market price.",
        "formula": "Intrinsic Value = √(22.5 × EPS × BVPS)",
        "interpretation": "If the market price sits well below intrinsic value, the stock may be "
                           "undervalued. If it sits well above, the stock may be overvalued relative "
                           "to Graham's formula.",
        "why_it_matters": "It anchors the whole margin-of-safety concept - without an estimate of "
                           "'true' worth, there's nothing to measure the current price against.",
    },
    "margin_of_safety": {
        "label": "Margin of Safety",
        "definition": "How far below its estimated intrinsic value a stock is currently trading.",
        "formula": "Margin of Safety = (Intrinsic Value − Market Price) / Intrinsic Value",
        "interpretation": "Graham recommended at least 33% margin of safety before buying, to protect "
                           "against estimation errors, bad luck, or events nobody could have predicted.",
        "why_it_matters": "It's Graham's central risk-management idea: buy cheap enough that even if "
                           "you're somewhat wrong about the value, you're unlikely to lose money.",
    },
    "pe_ratio": {
        "label": "P/E Ratio (Price-to-Earnings)",
        "definition": "How many years of current earnings it would take to 'pay back' the share price, "
                      "at today's profit level.",
        "formula": "P/E Ratio = Market Price per Share / Earnings Per Share",
        "interpretation": "Graham's defensive limit was 20x last year's earnings (or 25x the 7-year "
                           "average). Lower generally means cheaper relative to profit, but very low "
                           "P/E can also signal the market expects earnings to decline.",
        "why_it_matters": "It's the most widely used shorthand for 'is this stock expensive or cheap' "
                           "relative to how much money the company actually makes.",
    },
    "pb_ratio": {
        "label": "P/B Ratio (Price-to-Book)",
        "definition": "How the market price compares to the company's net asset (book) value per share.",
        "formula": "P/B Ratio = Market Price per Share / Book Value Per Share",
        "interpretation": "Graham's enterprising standard looked for P/B under roughly 1.2-1.5. A P/B "
                           "well above 3 often means the market is pricing in significant future growth "
                           "rather than current assets.",
        "why_it_matters": "It complements the P/E ratio by anchoring valuation to the balance sheet "
                           "rather than the income statement, which matters more for asset-heavy firms.",
    },
}


def render_metric_info(key, st_module):
    """
    Render an inline "info" expander/popover for one metric. Pass in the
    already-imported `streamlit` module as `st_module` to avoid a circular
    import at module load time.
    """
    st = st_module
    info = METRICS.get(key)
    if not info:
        return
    if hasattr(st, "popover"):
        with st.popover("ℹ️", use_container_width=False):
            _render_metric_body(info, st)
    else:
        with st.expander("ℹ️ What is this?"):
            _render_metric_body(info, st)


def _render_metric_body(info, st):
    st.markdown(f"**{info['label']}**")
    st.markdown(f"*Definition:* {info['definition']}")
    st.code(info["formula"], language="text")
    st.markdown(f"*Interpretation:* {info['interpretation']}")
    st.markdown(f"*Why it matters:* {info['why_it_matters']}")
