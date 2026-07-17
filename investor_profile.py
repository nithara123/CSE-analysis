"""
investor_profile.py
--------------------
Lets the user explicitly choose whether the app should score every company
using Benjamin Graham's Defensive Investor criteria or his Enterprising
Investor criteria - instead of the app silently deciding for them based on
how many years of financial history a company happens to have.

"Auto" preserves the original behaviour (Defensive if a company has >= 9
years of history, Enterprising otherwise) for anyone who doesn't want to
think about it. Picking "Defensive" or "Enterprising" explicitly pins
every score, badge, and comparison in the app to that one methodology, so
the same company can't show up scored one way on one page and a different
way on another.

Usage:
    from investor_profile import resolve_investor_type, render_profile_switcher

    # in the sidebar, once:
    render_profile_switcher()

    # anywhere a company needs to be scored:
    investor_type = resolve_investor_type(fd)   # -> "defensive" | "enterprising"
"""

import streamlit as st

from graham_engine import available_years

SESSION_KEY = "graham_profile_choice"
CHOICES = ["Auto", "Defensive", "Enterprising"]


def get_profile_choice() -> str:
    """Current global choice: 'Auto' | 'Defensive' | 'Enterprising'."""
    return st.session_state.get(SESSION_KEY, "Auto")


def resolve_investor_type(fd: dict) -> str:
    """
    Return 'defensive' or 'enterprising' for this company, respecting the
    user's explicit sidebar choice. Falls back to the original data-driven
    rule (>= 9 years of history -> defensive) only while the choice is
    left on "Auto".
    """
    choice = get_profile_choice()
    if choice == "Defensive":
        return "defensive"
    if choice == "Enterprising":
        return "enterprising"
    return "defensive" if available_years(fd) >= 9 else "enterprising"


def render_profile_switcher():
    """
    Renders the sidebar control that lets the user switch between Defensive,
    Enterprising, and Auto. Call this once from investor360_app.py.
    """
    st.markdown("**Investor Profile**")
    st.radio(
        "Score companies using...",
        CHOICES,
        index=CHOICES.index(get_profile_choice()),
        key=SESSION_KEY,
        help=(
            "Defensive: Graham's conservative criteria for passive investors "
            "(10 years of earnings/dividend history, current ratio >= 2.0, etc). "
            "Enterprising: Graham's criteria for more active investors "
            "(5 years of history, looser valuation limits). "
            "Auto: picks Defensive for companies with 9+ years of data on file, "
            "Enterprising otherwise - the app's original behaviour."
        ),
    )
    st.caption(
        "This choice controls Graham scoring, the AI Recommendation, and risk "
        "badges everywhere in the app - Dashboard, Discover, Company Workspace, "
        "Portfolio and Market Dashboard all use it consistently."
    )
