"""
pages/getting_started.py
--------------------------
Everything a first-time CSE investor needs before they touch a company
financial statement: what the CSE is, how investing works, how to open a
CDS account, broker comparison, and a step-by-step guide. The broker
comparison logic (cards, detail panel, fee/investment charts) is carried
over unchanged from the original app.py's "Broker Comparison" page.
"""

import base64
import os

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from graham_engine import fmt

LOGO_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "logos")


@st.cache_data(show_spinner=False)
def logo_b64(filename):
    if not filename:
        return None
    try:
        with open(os.path.join(LOGO_DIR, filename), "rb") as f:
            encoded = base64.b64encode(f.read()).decode()
        ext = filename.split(".")[-1].lower()
        return f"data:image/{ext};base64,{encoded}"
    except FileNotFoundError:
        return None


def render(data, companies, sectors, brokers, profile):
    st.markdown("## Getting Started")
    st.caption("Everything you need before placing your first trade on the Colombo Stock Exchange.")

    tabs = st.tabs(["CSE Basics", "How Investing Works", "Opening a CDS Account",
                    "Broker Comparison", "Step-by-Step Guide"])

    with tabs[0]:
        st.markdown("""
        <div class="section-card">
        <h3>What is the Colombo Stock Exchange?</h3>
        <p style="color:#5a7199;">
        The Colombo Stock Exchange (CSE) is Sri Lanka's only licensed stock exchange, where shares of
        publicly listed companies are bought and sold. It's regulated by the Securities and Exchange
        Commission of Sri Lanka (SEC) and operates on business days, with prices moving continuously
        based on buyer and seller demand.
        </p>
        <p style="color:#5a7199;">
        Investor 360 exists to help you understand a company <em>before</em> you invest in it - it does
        not place trades for you.
        </p>
        </div>""", unsafe_allow_html=True)

    with tabs[1]:
        st.markdown("""
        <div class="section-card">
        <h3>How Investing Works</h3>
        <p style="color:#5a7199;">When you buy a share, you own a small slice of that company. Your
        return comes from two places:</p>
        <ul style="color:#5a7199;">
            <li><strong>Capital appreciation</strong> - the share price rising above what you paid.</li>
            <li><strong>Dividends</strong> - a portion of profits the company pays out to shareholders.</li>
        </ul>
        <p style="color:#5a7199;">Both come with risk: prices can fall as well as rise, and dividends
        are never guaranteed. Diversifying across multiple companies and sectors, and only investing
        money you won't need in the short term, are two of the simplest ways to manage that risk.</p>
        </div>""", unsafe_allow_html=True)

    with tabs[2]:
        st.markdown("""
        <div class="section-card">
        <h3>How to Open a CDS Account</h3>
        <p style="color:#5a7199;">A Central Depository System (CDS) account holds your shares
        electronically. You cannot buy CSE shares without one. In short:</p>
        <ol style="color:#5a7199;">
            <li>Choose a licensed stockbroker (see the Broker Comparison tab).</li>
            <li>Complete the broker's account-opening form, along with your NIC/passport and proof of address.</li>
            <li>The broker opens both a CDS account and a trading account on your behalf.</li>
            <li>Fund your trading account, and you're ready to place your first order through the broker.</li>
        </ol>
        </div>""", unsafe_allow_html=True)

    with tabs[3]:
        _render_broker_comparison(brokers)

    with tabs[4]:
        st.markdown("""
        <div class="section-card">
        <h3>Step-by-Step Investment Guide</h3>
        <ol style="color:#5a7199;line-height:1.9;">
            <li><strong>Learn the basics</strong> - work through the tabs above and the Learning Centre.</li>
            <li><strong>Open a CDS + trading account</strong> with a broker that fits your budget and platform preference.</li>
            <li><strong>Research companies</strong> using Discover Companies - filter by sector, check the AI Score and Benjamin Graham result.</li>
            <li><strong>Read the full picture</strong> in the Company Workspace - financials, news, and risk, not just the price.</li>
            <li><strong>Build a watchlist</strong> in Portfolio before committing real money.</li>
            <li><strong>Place your first order</strong> through your broker's platform once you're comfortable.</li>
            <li><strong>Review periodically</strong> - re-check your holdings against fresh financials and news, don't "set and forget."</li>
        </ol>
        </div>""", unsafe_allow_html=True)


def _render_broker_comparison(brokers):
    df_b = pd.DataFrame(brokers)

    def parse_min(val):
        try:
            return float(str(val).replace(",", "").replace(" ", ""))
        except Exception:
            return 0.0

    df_b["min_numeric"] = df_b["min_investment_raw"].apply(parse_min)

    fc1, fc2 = st.columns(2)
    with fc1:
        max_inv = int(df_b["min_numeric"].max()) or 1000000
        dep_filter = st.slider("Maximum Minimum Investment (LKR)", 0, max_inv, max_inv, step=5000, key="gs_dep_filter")
    with fc2:
        platforms = ["All"] + sorted(df_b["online_platform"].dropna().unique().tolist())
        plat_filter = st.selectbox("Online Platform", platforms, key="gs_plat_filter")

    filtered = df_b[df_b["min_numeric"] <= dep_filter]
    if plat_filter != "All":
        filtered = filtered[filtered["online_platform"] == plat_filter]

    st.markdown(f"**{len(filtered)} broker(s) match your filters.**")
    st.divider()

    if "selected_broker" not in st.session_state:
        st.session_state.selected_broker = None

    PER_PAGE = 9
    total_pages = max(1, -(-len(filtered) // PER_PAGE))
    if "broker_page" not in st.session_state:
        st.session_state.broker_page = 1
    st.session_state.broker_page = min(st.session_state.broker_page, total_pages)

    grid_col, detail_col = st.columns([2, 1])

    with grid_col:
        start = (st.session_state.broker_page - 1) * PER_PAGE
        page_rows = filtered.iloc[start:start + PER_PAGE].to_dict("records")

        for row_start in range(0, len(page_rows), 3):
            cols = st.columns(3)
            for col, b in zip(cols, page_rows[row_start:row_start + 3]):
                with col:
                    logo_uri = logo_b64(b.get("logo"))
                    avatar_html = (f'<img class="broker-avatar" src="{logo_uri}">' if logo_uri
                                   else '<div class="broker-avatar" style="display:flex;align-items:center;justify-content:center;background:#0B1D51;color:white;font-weight:700;">'
                                        f'{b["name"][0]}</div>')
                    st.markdown(f"""
                    <div class="broker-card">
                        {avatar_html}
                        <div class="broker-name">{b['name']}</div>
                        <div class="broker-fee">{fmt(b.get('brokerage_fee_percent'), suffix='%')} Commission</div>
                        <div class="broker-contact" style="font-size:0.60rem;">
                            📞 {b.get('phone') or '—'}<br>
                            ✉️ {b.get('email') or '—'}<br>
                            🌐 {(b.get('website') or '—')[:28]}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)
                    if st.button("View Details", key=f"gs_view_{b['name']}", use_container_width=True):
                        st.session_state.selected_broker = b["name"]
                        st.rerun()

        st.write("")
        pg1, pg2, pg3 = st.columns([1, 2, 1])
        with pg1:
            if st.button("◀ Prev", disabled=st.session_state.broker_page <= 1, use_container_width=True, key="gs_prev"):
                st.session_state.broker_page -= 1
                st.rerun()
        with pg2:
            st.markdown(f"<div style='text-align:center;color:#5a7199;padding-top:6px;'>Page {st.session_state.broker_page} of {total_pages}</div>", unsafe_allow_html=True)
        with pg3:
            if st.button("Next ▶", disabled=st.session_state.broker_page >= total_pages, use_container_width=True, key="gs_next"):
                st.session_state.broker_page += 1
                st.rerun()

    with detail_col:
        sel_name = st.session_state.selected_broker
        sel = next((b for b in brokers if b["name"] == sel_name), None) if sel_name else None

        if sel is None:
            st.markdown("""
            <div class="broker-detail-panel" style="text-align:center; color:#5a7199;">
                Click <strong>View Details</strong> on any broker card to see their full profile here.
            </div>""", unsafe_allow_html=True)
        else:
            logo_uri = logo_b64(sel.get("logo"))
            avatar_html = (f'<img class="broker-detail-avatar" src="{logo_uri}">' if logo_uri
                           else '<div class="broker-detail-avatar" style="display:flex;align-items:center;justify-content:center;background:#0B1D51;color:white;font-weight:700;">'
                                f'{sel["name"][0]}</div>')
            st.markdown(f"""
            <div class="broker-detail-panel">
                <div style="overflow:auto;">
                    {avatar_html}
                    <div>
                        <div style="font-weight:700;color:#0B1D51;font-size:1rem;">{sel['name']}</div>
                        <span class="broker-badge">CSE Registered Broker</span>
                    </div>
                </div>
                <div style="margin-top:14px; font-size:0.82rem; color:#5a7199; line-height:1.9;">
                    📞 {sel.get('phone') or '—'}<br>
                    ✉️ {sel.get('email') or '—'}<br>
                    🌐 {sel.get('website') or '—'}<br>
                    📍 {sel.get('address') or '—'}
                </div>
                <hr style="border-color:#e0e7ef;">
                <div style="font-weight:700;color:#0B1D51;font-size:0.88rem;margin-bottom:6px;">About the Broker</div>
                <div style="font-size:0.82rem;color:#5a7199;line-height:1.6;">{sel.get('about') or 'No description available.'}</div>
                <hr style="border-color:#e0e7ef;">
                <div style="font-weight:700;color:#0B1D51;font-size:0.88rem;margin-bottom:6px;">Commission &amp; Platform</div>
                <div style="font-size:0.82rem;color:#5a7199;line-height:1.9;">
                    Brokerage Fee: <strong style="color:#0B1D51;">{fmt(sel.get('brokerage_fee_percent'), suffix='%')}</strong><br>
                    Online Platform: <strong style="color:#0B1D51;">{sel.get('online_platform') or '—'}</strong><br>
                    Research Support: <strong style="color:#0B1D51;">{sel.get('research_support') or '—'}</strong>
                </div>
                <div style="font-weight:700;color:#0B1D51;font-size:0.88rem;margin-top:14px;">Minimum Investment</div>
                <div class="broker-min-box">{sel.get('min_investment_raw') or 'N/A'}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("✕ Close", use_container_width=True, key="gs_close"):
                st.session_state.selected_broker = None
                st.rerun()

    st.divider()
    st.markdown("### Fee &amp; Investment Analytics")
    ch1, ch2 = st.columns(2)
    with ch1:
        st.markdown("#### Brokerage Fee (%)")
        df_fee = filtered.dropna(subset=["brokerage_fee_percent"]).sort_values("brokerage_fee_percent")
        if not df_fee.empty:
            min_fee = df_fee["brokerage_fee_percent"].min()
            colors_fee = ["#16a34a" if v == min_fee else "#0B1D51" for v in df_fee["brokerage_fee_percent"]]
            fig = go.Figure(go.Bar(x=df_fee["brokerage_fee_percent"], y=df_fee["name"], orientation="h",
                marker_color=colors_fee, text=[f"{v}%" for v in df_fee["brokerage_fee_percent"]],
                textposition="outside", textfont=dict(color="#5a7199", size=10)))
            fig.update_layout(paper_bgcolor="#ffffff", plot_bgcolor="#F8F9FB", font=dict(color="#5a7199"),
                xaxis=dict(gridcolor="#e5eaf2", title="Fee %"), yaxis=dict(gridcolor="#e5eaf2"),
                margin=dict(l=10, r=10, t=20, b=10), height=max(300, len(df_fee) * 40))
            st.plotly_chart(fig, use_container_width=True)
            st.caption("Green = lowest fee.")
    with ch2:
        st.markdown("#### Minimum Investment (LKR)")
        df_inv = filtered[filtered["min_numeric"] > 0].sort_values("min_numeric")
        if not df_inv.empty:
            fig = go.Figure(go.Bar(x=df_inv["min_numeric"], y=df_inv["name"], orientation="h",
                marker_color="#2563eb", text=[f"LKR {v:,.0f}" for v in df_inv["min_numeric"]],
                textposition="outside", textfont=dict(color="#5a7199", size=10)))
            fig.update_layout(paper_bgcolor="#ffffff", plot_bgcolor="#F8F9FB", font=dict(color="#5a7199"),
                xaxis=dict(gridcolor="#e5eaf2", title="LKR"), yaxis=dict(gridcolor="#e5eaf2"),
                margin=dict(l=10, r=10, t=20, b=10), height=max(300, len(df_inv) * 40))
            st.plotly_chart(fig, use_container_width=True)
