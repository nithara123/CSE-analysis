"""
pages/discover.py
-------------------
Browse or filter-by-sector, then see beginner-friendly company cards
(name, sector, price, AI score, Graham result, news sentiment, risk,
quick recommendation) rather than a dense spreadsheet-style table.
"""

import streamlit as st

from graham_engine import score_defensive, score_enterprising, available_years
from ai_engine import compute_ai_recommendation
from ui_components import render_company_card
from portfolio_store import load_portfolio, add_company
from investor_profile import resolve_investor_type


def _ai_for(fd):
    return compute_ai_recommendation(fd, investor_type=resolve_investor_type(fd))


def render(data, companies, sectors, profile, go_to):
    st.markdown("## Discover Companies")
    st.caption("Browse every listed company, or narrow down by sector first.")

    mode = st.radio("Browse mode", ["All Companies", "By Sector"], horizontal=True, label_visibility="collapsed")

    if mode == "By Sector":
        sector_names = sorted(sectors.keys())
        chosen_sectors = st.multiselect("Choose one or more sectors", sector_names)
        if not chosen_sectors:
            st.info("Select at least one sector above to see companies.")
            return
        candidate_names = []
        for s in chosen_sectors:
            candidate_names.extend(sectors.get(s, {}).get("companies", []))
        candidate_names = sorted(set(candidate_names))
    else:
        candidate_names = sorted(companies.keys())

    search = st.text_input("Search by name", placeholder="Start typing a company name...")
    if search:
        candidate_names = [n for n in candidate_names if search.lower() in n.lower()]

    sort_by = st.selectbox("Sort by", ["AI Score (High to Low)", "Name (A-Z)"])

    st.caption(f"{len(candidate_names)} compan{'y' if len(candidate_names)==1 else 'ies'} match your filters.")
    st.divider()

    if not candidate_names:
        st.info("No companies match the current filters.")
        return

    portfolio = set(load_portfolio())

    PER_PAGE = 12
    if "discover_page" not in st.session_state:
        st.session_state.discover_page = 1

    # Score everything up-front (cheap - pure arithmetic on already-loaded JSON)
    scored = []
    for name in candidate_names:
        fd = companies.get(name, {})
        if not fd:
            continue
        ai = _ai_for(fd)
        scored.append((name, fd, ai))

    if sort_by.startswith("AI Score"):
        scored.sort(key=lambda t: t[2]["score"], reverse=True)
    else:
        scored.sort(key=lambda t: t[0])

    total_pages = max(1, -(-len(scored) // PER_PAGE))
    st.session_state.discover_page = min(st.session_state.discover_page, total_pages)
    start = (st.session_state.discover_page - 1) * PER_PAGE
    page_items = scored[start:start + PER_PAGE]

    cols_per_row = 3
    for row_start in range(0, len(page_items), cols_per_row):
        cols = st.columns(cols_per_row)
        for col, (name, fd, ai) in zip(cols, page_items[row_start:row_start + cols_per_row]):
            with col:
                action = render_company_card(name, fd, ai, in_portfolio=(name in portfolio), key_prefix="discover")
                if action == "view":
                    st.session_state.workspace_company = name
                    go_to("Company Workspace")
                elif action == "add":
                    add_company(name)
                    st.rerun()

    st.write("")
    p1, p2, p3 = st.columns([1, 2, 1])
    with p1:
        if st.button("◀ Prev", disabled=st.session_state.discover_page <= 1, use_container_width=True):
            st.session_state.discover_page -= 1
            st.rerun()
    with p2:
        st.markdown(f"<div style='text-align:center;color:#8B93AD;padding-top:6px;'>Page {st.session_state.discover_page} of {total_pages}</div>", unsafe_allow_html=True)
    with p3:
        if st.button("Next ▶", disabled=st.session_state.discover_page >= total_pages, use_container_width=True):
            st.session_state.discover_page += 1
            st.rerun()
