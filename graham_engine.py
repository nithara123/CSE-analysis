"""
graham_engine.py
----------------
Benjamin Graham scoring engine, extracted UNCHANGED from the original
Investor 360 app.py. Every calculation, threshold and point value below
is byte-for-byte identical to the original implementation - only the
surrounding architecture changed (this now lives in its own module so
the UI layer can import it instead of everything living in one file).

Do not "clean up" or "simplify" the thresholds in here without checking
with whoever owns the financial methodology - these numbers encode the
actual Graham Defensive / Enterprising Investor criteria the app is
built around.
"""

# ── Data helpers ──────────────────────────────────────────────────────────────

def get_series(fd, *keys):
    d = fd
    for k in keys:
        if not isinstance(d, dict):
            return {}
        d = d.get(k, {})
    if not isinstance(d, dict):
        return {}
    return {y: v for y, v in d.items() if v is not None}


def latest(s):
    if not s:
        return None
    return s.get(max(s.keys()))


def n_years(s, n):
    """Return values from the most recent n years."""
    if not s:
        return {}
    yrs = sorted(s.keys(), reverse=True)[:n]
    return {y: s[y] for y in yrs}


def all_positive(s):
    if not s:
        return False
    return all(v > 0 for v in s.values())


def any_positive(s):
    return any(v > 0 for v in s.values()) if s else False


def fmt(val, prefix="", suffix="", dec=2):
    if val is None:
        return "N/A"
    try:
        return f"{prefix}{val:,.{dec}f}{suffix}"
    except Exception:
        return "N/A"


def fmt_large(val):
    if val is None:
        return "N/A"
    try:
        if abs(val) >= 1e9:
            return f"LKR {val/1e9:,.2f}B"
        if abs(val) >= 1e6:
            return f"LKR {val/1e6:,.2f}M"
        if abs(val) >= 1e3:
            return f"LKR {val/1e3:,.1f}K"
        return f"LKR {val:,.0f}"
    except Exception:
        return "N/A"


def available_years(fd):
    """Returns how many years of data the company has."""
    years = fd.get("years", [])
    return len(years)


# ═══════════════════════════════════════════════════════════════════════════
# SCORING ENGINES  (unchanged from the original app.py)
# ═══════════════════════════════════════════════════════════════════════════

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

    # 7. Company Size / Quality — 10 pts
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
