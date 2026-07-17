"""
macro_signals.py
-----------------
Lightweight, resilient macro signals used to (a) feed the AI Recommendation
Engine's "Macro Conditions" component, and (b) show one genuinely live
number - the USD/LKR spot rate - on the Market Dashboard.

WHY THIS ISN'T A DIRECT CBSL INTEGRATION
-----------------------------------------
CBSL (Central Bank of Sri Lanka) does not publish a public, documented
JSON/REST API the way the World Bank does. Its Daily/Weekly/Monthly
Indicators pages are either static HTML tables refreshed on their own
schedule, or client-side search widgets - e.g.
https://www.cbsl.gov.lk/cbsl_custom/exrates/exrates_spot_mid.php - whose
"Submit" button resolves data via an internal JS/AJAX call rather than a
fetchable GET endpoint. Scraping that would mean reverse-engineering an
internal implementation detail that can change without notice, not
integrating with a stable interface - the kind of thing that looks like
it works in testing and then silently breaks in front of a customer.

So instead:
  - The live USD/LKR rate below comes from a free, key-less FX aggregator
    (open.er-api.com) that actually is a real API. It's a market rate, not
    officially CBSL's indicative rate, so it's labelled that way in the UI.
  - The slower-moving indicators (inflation trend, GDP growth direction)
    still use the World Bank series already wired up in news_intelligence.py.
    CBSL publishes those on essentially the same annual/quarterly cadence -
    the "staleness" isn't a World-Bank-specific problem, it's how often Sri
    Lanka's own statistics offices report the underlying number in the
    first place. Swapping the data source wouldn't make the number newer.

If CBSL ever publishes a real API (or you have credentials/access to one
that isn't public), swap the implementation of estimate_macro_outlook()
below - nothing else in the app needs to change, since every caller only
depends on this function returning "positive" | "neutral" | "negative" | None.
"""

import requests
import streamlit as st

FX_API_URL = "https://open.er-api.com/v6/latest/USD"


@st.cache_data(ttl=1800, show_spinner=False)
def fetch_live_usd_lkr():
    """Live USD/LKR spot rate from a free, no-key FX aggregator.
    Returns (rate, as_of_utc_string) or (None, None) on any failure -
    callers should always handle the None case gracefully."""
    try:
        resp = requests.get(FX_API_URL, timeout=8)
        resp.raise_for_status()
        payload = resp.json()
        rate = (payload.get("rates") or {}).get("LKR")
        as_of = payload.get("time_last_update_utc")
        if rate is None:
            return None, None
        return round(float(rate), 2), as_of
    except Exception:
        return None, None


@st.cache_data(ttl=86400, show_spinner=False)
def _wb_series(iso3, indicator, start_year=2015):
    """Minimal standalone World Bank series fetch (kept separate from
    news_intelligence.py's copy so this module has no dependency on it)."""
    try:
        url = (f"https://api.worldbank.org/v2/country/{iso3}/indicator/"
               f"{indicator}?format=json&date={start_year}:2030&per_page=100")
        resp = requests.get(url, timeout=8)
        resp.raise_for_status()
        payload = resp.json()
        if not isinstance(payload, list) or len(payload) < 2 or not payload[1]:
            return {}
        series = {}
        for row in payload[1]:
            v, y = row.get("value"), row.get("date")
            if v is not None and y:
                series[int(y)] = v
        return series
    except Exception:
        return {}


@st.cache_data(ttl=86400, show_spinner=False)
def estimate_macro_outlook():
    """
    A coarse 'positive' / 'neutral' / 'negative' read on Sri Lanka's macro
    backdrop, used only as a directional weight in the AI Recommendation
    Score - not investment advice on its own. Built from two World Bank
    series: inflation (CPI, YoY) and GDP growth.

    Rule of thumb:
      - Inflation falling by 1+ pt AND/OR GDP growth > 2% -> pushes positive
      - Inflation rising by 1+ pt AND/OR GDP growth < 0% -> pushes negative
      - Otherwise, or if no data at all -> neutral / None
    """
    infl = _wb_series("LKA", "FP.CPI.TOTL.ZG")
    gdp = _wb_series("LKA", "NY.GDP.MKTP.KD.ZG")
    if not infl and not gdp:
        return None

    signal = 0
    votes = 0
    if len(infl) >= 2:
        years = sorted(infl.keys())
        latest_infl, prev_infl = infl[years[-1]], infl[years[-2]]
        votes += 1
        if latest_infl < prev_infl - 1:
            signal += 1
        elif latest_infl > prev_infl + 1:
            signal -= 1
    if gdp:
        latest_gdp = gdp[max(gdp.keys())]
        votes += 1
        if latest_gdp > 2:
            signal += 1
        elif latest_gdp < 0:
            signal -= 1

    if votes == 0:
        return None
    if signal > 0:
        return "positive"
    if signal < 0:
        return "negative"
    return "neutral"
