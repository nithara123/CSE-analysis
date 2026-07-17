"""
ai_engine.py
------------
The new "AI Recommendation Score" required by the redesign brief.

This is genuinely NEW logic (the brief explicitly asks for it) - it sits
ON TOP of the existing, untouched Graham engine rather than replacing it.
It never invents numbers silently: every score this module returns comes
back with a `components` breakdown and a plain-English `explanation`
paragraph, so nothing is an "unexplained score" (per the brief).

Inputs are all optional except `fd` (the company's financial dict) - the
engine degrades gracefully and says so in the explanation when a signal
(news, price history, sector average, macro) isn't available, rather than
pretending it evaluated something it didn't.

    from ai_engine import compute_ai_recommendation
    result = compute_ai_recommendation(
        fd, investor_type="defensive",
        news_sentiment_counts={"positive": 4, "neutral": 2, "negative": 1},
        price_series=daily_close_prices,   # list[float], oldest->newest
        sector_avg_score=62.4,
    )
    result["score"], result["recommendation"], result["explanation"], result["components"]
"""

import statistics

from graham_engine import (
    score_defensive, score_enterprising, get_series, latest, fmt,
)

# Relative weight of each signal in the final 0-100 score.
# These sum to 1.0. If a signal is unavailable its weight is
# redistributed proportionally across the signals that ARE available,
# rather than silently treating a missing signal as zero/negative.
#
# Valuation (margin of safety / P/E) is folded INTO the Graham component
# rather than scored as its own separate line - it's already one of
# Graham's own criteria (Margin of Safety >= 33%, P/E limits, etc.), so
# scoring it twice double-counted the same signal. News Sentiment is not
# used as a scored/weighted signal at all (it still appears as its own
# section further down the Company Workspace page - it's just not part of
# the numeric score), since reliable, dated coverage isn't available for
# every company. Benjamin Graham's methodology is the backbone of this
# score, so it carries the majority weight.
WEIGHTS = {
    "graham":      0.60,   # Benjamin Graham score, including margin of safety / valuation
    "sector":      0.15,   # how the company sits relative to its sector peers
    "macro":       0.10,   # macroeconomic backdrop (inflation, rates, growth)
    "price_trend": 0.10,   # recent share price momentum
    "volatility":  0.05,   # inverse of recent price volatility (stability bonus)
}


def _valuation_note(fd):
    """Margin of safety / P/E, folded into the Graham component's own note
    rather than scored as a separate signal - Graham's criteria already
    include a Margin of Safety and P/E check, so this only adds context
    to the Graham note, never a second score for the same thing."""
    mos = latest(get_series(fd, "graham_analysis", "margin_of_safety"))
    pe = latest(get_series(fd, "market_metrics", "pe_ratio"))
    notes = []
    if mos is not None:
        notes.append(f"a margin of safety of {mos:.1%}")
    if pe is not None and pe > 0:
        notes.append(f"a P/E ratio of {pe:.1f}")
    return " and ".join(notes)


def _graham_component(fd, investor_type):
    if investor_type == "enterprising":
        total, criteria = score_enterprising(fd)
    else:
        total, criteria = score_defensive(fd)
    return total, criteria  # already 0-100


def _sector_component(graham_total, sector_avg_score):
    if sector_avg_score is None:
        return None, "no sector benchmark available"
    diff = graham_total - sector_avg_score
    score = max(0.0, min(100.0, 50 + diff * 2.5))
    if diff > 5:
        note = f"outperforming its sector average ({sector_avg_score:.0f}) by {diff:.0f} points"
    elif diff < -5:
        note = f"underperforming its sector average ({sector_avg_score:.0f}) by {abs(diff):.0f} points"
    else:
        note = f"roughly in line with its sector average ({sector_avg_score:.0f})"
    return round(score, 1), note


def _macro_component(macro_outlook):
    """macro_outlook: 'positive' | 'neutral' | 'negative' | None (e.g. derived
    from inflation/interest-rate direction on the Market Dashboard)."""
    mapping = {"positive": (75.0, "a supportive macroeconomic backdrop"),
               "neutral":  (55.0, "a broadly neutral macroeconomic backdrop"),
               "negative": (30.0, "a challenging macroeconomic backdrop")}
    if macro_outlook not in mapping:
        return None, "no macroeconomic signal available"
    return mapping[macro_outlook]


def _price_trend_component(price_series):
    if not price_series or len(price_series) < 2:
        return None, None, "insufficient price history"
    change_pct = (price_series[-1] - price_series[0]) / price_series[0] if price_series[0] else 0
    score = max(0.0, min(100.0, 50 + change_pct * 250))  # +20% -> 100, -20% -> 0
    direction = "upward" if change_pct > 0.02 else ("downward" if change_pct < -0.02 else "flat")
    return round(score, 1), change_pct, f"a {direction} price trend ({change_pct:+.1%} over the period)"


def _volatility_component(price_series):
    if not price_series or len(price_series) < 3:
        return None, None, "insufficient price history to assess volatility"
    returns = [
        (price_series[i] - price_series[i - 1]) / price_series[i - 1]
        for i in range(1, len(price_series)) if price_series[i - 1]
    ]
    if len(returns) < 2:
        return None, None, "insufficient price history to assess volatility"
    vol = statistics.pstdev(returns)
    # Lower daily volatility -> higher stability score. ~0% -> 100, ~5%+ -> 0.
    score = max(0.0, min(100.0, 100 - vol * 2000))
    risk_label = "Low" if vol < 0.012 else ("Medium" if vol < 0.025 else "High")
    return round(score, 1), risk_label, f"{risk_label.lower()} recent price volatility"


def compute_sector_average_graham(sector_company_names, companies, investor_type="defensive"):
    """
    Average Graham score across a company's sector peers, used to feed the
    'Sector Performance' component. Reuses score_defensive/score_enterprising
    exactly as-is on each peer (same investor-type-by-data-availability rule
    used everywhere else in the app) - this is new orchestration on top of
    the untouched Graham engine, not a change to the Graham logic itself.
    Returns None if no peer could be scored.
    """
    scores = []
    for name in sector_company_names:
        fd = companies.get(name)
        if not fd:
            continue
        try:
            years = len(fd.get("years", []))
            peer_type = investor_type if years >= 9 else "enterprising"
            total, _ = _graham_component(fd, peer_type)
            scores.append(total)
        except Exception:
            continue
    if not scores:
        return None
    return sum(scores) / len(scores)


def _recommendation_label(score):
    if score >= 80:
        return "Strong Buy"
    if score >= 65:
        return "Buy"
    if score >= 45:
        return "Hold"
    if score >= 30:
        return "Avoid"
    return "Sell"


def compute_ai_recommendation(fd, investor_type="defensive",
                               news_sentiment_counts=None,
                               price_series=None,
                               sector_avg_score=None,
                               macro_outlook=None):
    """
    Compute the blended AI Recommendation Score for one company.

    Returns a dict:
        score          float 0-100
        recommendation str  ("Strong Buy" | "Buy" | "Hold" | "Avoid" | "Sell")
        explanation    str  human-readable paragraph explaining the WHY
        components     list of {name, score, weight, note} - one per signal,
                        including signals that were skipped (score=None) so
                        the UI can show what wasn't available.
        risk_rating    str  ("Low" | "Medium" | "High") derived from volatility
                        + Graham's own debt/liquidity checks.
        graham_total   float the underlying, unmodified Graham score (0-100)
    """
    graham_total, graham_criteria = _graham_component(fd, investor_type)
    val_note = _valuation_note(fd)
    sector_score, sector_note = _sector_component(graham_total, sector_avg_score)
    macro_score, macro_note = _macro_component(macro_outlook)
    price_score, price_change, price_note = _price_trend_component(price_series)
    vol_score, vol_risk_label, vol_note = _volatility_component(price_series)

    raw_components = {
        "graham":      graham_total,
        "sector":      sector_score,
        "macro":       macro_score,
        "price_trend": price_score,
        "volatility":  vol_score,
    }
    available = {k: v for k, v in raw_components.items() if v is not None}
    available_weight = sum(WEIGHTS[k] for k in available)
    if available_weight == 0:
        final_score = graham_total  # absolute fallback: Graham score alone
    else:
        final_score = sum(available[k] * (WEIGHTS[k] / available_weight) for k in available)
    final_score = round(max(0.0, min(100.0, final_score)), 1)

    # Debt ratio / current ratio from Graham's own criteria are the risk
    # rating's ONLY inputs. This is deliberate: these fundamentals are
    # always available (they come straight from the loaded JSON), so the
    # risk badge is identical for a given company no matter which page
    # you're looking at it from.
    #
    # Recent price volatility is still surfaced (see vol_risk_label /
    # vol_note below) as its own "Volatility / Stability" line in the AI
    # score breakdown - it's just deliberately kept OUT of this headline
    # risk_rating. Volatility is only ever computed on the Company
    # Workspace page (it requires a live price-history fetch per company,
    # which isn't done for every card on Discover/Portfolio for
    # performance reasons). Letting it feed risk_rating meant the exact
    # same company could show "Low Risk" on Discover Companies (no price
    # data fetched -> fundamentals only) and "High Risk" on Company
    # Workspace (price data fetched -> volatility pushed it up) - a
    # confusing, contradictory bug. Keeping risk_rating fundamentals-only
    # fixes that: it's the same badge everywhere.
    dr_v = latest(get_series(fd, "ratios", "debt_ratio"))
    cr_v = latest(get_series(fd, "ratios", "current_ratio"))
    fundamentals_risk = "Low"
    if (dr_v is not None and dr_v >= 0.65) or (cr_v is not None and cr_v < 1.0):
        fundamentals_risk = "High"
    elif (dr_v is not None and dr_v >= 0.5) or (cr_v is not None and cr_v < 1.5):
        fundamentals_risk = "Medium"
    risk_rating = fundamentals_risk

    graham_note = f"a Graham {investor_type} score of {graham_total}/100"
    if val_note:
        graham_note += f", including {val_note}"

    notes = {
        "graham": graham_note,
        "sector": sector_note,
        "macro": macro_note,
        "price_trend": price_note,
        "volatility": vol_note,
    }
    used_notes = [notes[k] for k in ["graham", "sector", "macro", "price_trend", "volatility"]
                  if raw_components.get(k) is not None]
    skipped = [k for k, v in raw_components.items() if v is None]

    recommendation = _recommendation_label(final_score)

    explanation_parts = [
        f"This company scores {final_score:.0f}/100 overall, translating to a **{recommendation}** recommendation.",
    ]
    if used_notes:
        joined = "; ".join(used_notes[:-1]) + (f"; and {used_notes[-1]}" if len(used_notes) > 1 else used_notes[0])
        explanation_parts.append(f"The score reflects {joined}.")
    explanation_parts.append(f"Overall risk is rated **{risk_rating}**, based on leverage and liquidity "
                              "(debt ratio and current ratio) - this stays the same everywhere the company "
                              "appears in the app."
                              + (f" Recent price movement has also been {vol_note}, which is factored into "
                                 "the score above but does not change the risk rating." if vol_risk_label else ""))
    if skipped:
        pretty = {"graham": "Graham score", "sector": "sector comparison",
                  "macro": "macroeconomic conditions", "price_trend": "price trend",
                  "volatility": "volatility"}
        explanation_parts.append(
            "Note: " + ", ".join(pretty[k] for k in skipped) +
            (" were" if len(skipped) > 1 else " was") +
            " not available and so did not factor into this score."
        )
    explanation = " ".join(explanation_parts)

    components = [
        {"name": "Benjamin Graham Score", "key": "graham", "score": raw_components["graham"],
         "weight": WEIGHTS["graham"], "note": notes["graham"]},
        {"name": "Sector Performance", "key": "sector", "score": raw_components["sector"],
         "weight": WEIGHTS["sector"], "note": notes["sector"]},
        {"name": "Macro Conditions", "key": "macro", "score": raw_components["macro"],
         "weight": WEIGHTS["macro"], "note": notes["macro"]},
        {"name": "Price Trend", "key": "price_trend", "score": raw_components["price_trend"],
         "weight": WEIGHTS["price_trend"], "note": notes["price_trend"]},
        {"name": "Volatility / Stability", "key": "volatility", "score": raw_components["volatility"],
         "weight": WEIGHTS["volatility"], "note": notes["volatility"]},
    ]

    return {
        "score": final_score,
        "recommendation": recommendation,
        "explanation": explanation,
        "components": components,
        "risk_rating": risk_rating,
        "graham_total": graham_total,
        "graham_criteria": graham_criteria,
    }


def natural_language_summary(fd, ai_result, company_name="This company"):
    """
    Short, beginner-friendly paragraph for the top of the Company Workspace -
    the "This company demonstrates strong earnings consistency..." text the
    brief asks for. Built from the same underlying signals as the AI score,
    so it never contradicts the numbers shown alongside it.
    """
    eps_s = get_series(fd, "income_statement", "eps")
    cr_v = latest(get_series(fd, "ratios", "current_ratio"))
    dr_v = latest(get_series(fd, "ratios", "debt_ratio"))
    mos_v = latest(get_series(fd, "graham_analysis", "margin_of_safety"))

    fragments = []
    if eps_s:
        recent = sorted(eps_s.items())[-5:]
        if recent and all(v > 0 for _, v in recent):
            fragments.append("strong earnings consistency")
        elif recent and any(v > 0 for _, v in recent):
            fragments.append("mixed earnings consistency")
        else:
            fragments.append("weak recent earnings")
    if cr_v is not None:
        fragments.append("healthy liquidity" if cr_v >= 1.5 else "tight liquidity")
    if dr_v is not None:
        fragments.append("moderate debt levels" if dr_v < 0.6 else "elevated debt levels")
    if mos_v is not None:
        fragments.append("an attractive valuation with a real margin of safety" if mos_v >= 0.2
                          else "limited margin of safety at current prices")

    if not fragments:
        return (f"{company_name} does not yet have enough financial history on record for a detailed "
                f"narrative summary. Explore the Financial Overview and Benjamin Graham sections below "
                f"for what data is available.")

    body = ", ".join(fragments[:-1]) + (f", and {fragments[-1]}" if len(fragments) > 1 else fragments[0])
    verdict = {
        "Strong Buy": "making it a compelling candidate for further research.",
        "Buy": "making it a potentially attractive long-term investment.",
        "Hold": "suggesting a wait-and-watch approach may be prudent.",
        "Avoid": "suggesting caution before committing new capital.",
        "Sell": "suggesting existing holders may want to reassess their position.",
    }.get(ai_result.get("recommendation"), "worth reviewing further before investing.")

    return f"{company_name} demonstrates {body}, {verdict}"
