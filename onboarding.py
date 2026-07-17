"""
onboarding.py
-------------
First-time-user onboarding assistant for Investor 360.

Shown once, ever, per installation (see preferences.py for how that's
persisted to disk). Collects a lightweight investor profile that the rest
of the app (Discover Companies recommendations, Dashboard framing, tone of
the AI explanations) can read via `preferences.load_profile()`.

Usage from app.py:

    from preferences import load_profile
    from onboarding import render_onboarding

    profile = load_profile()
    if not profile["onboarding_complete"]:
        render_onboarding()
        st.stop()   # don't render the rest of the app until onboarding finishes
"""

import streamlit as st
from preferences import mark_onboarding_complete

STEPS = ["experience", "cds", "type", "goal", "risk"]


def _init_state():
    if "onboarding_step" not in st.session_state:
        st.session_state.onboarding_step = 0
    if "onboarding_answers" not in st.session_state:
        st.session_state.onboarding_answers = {}


def _progress_bar():
    step = st.session_state.onboarding_step
    st.progress((step) / len(STEPS), text=f"Step {min(step+1, len(STEPS))} of {len(STEPS)}")


def _next_step():
    st.session_state.onboarding_step += 1
    st.rerun()


def render_onboarding():
    """Renders the full onboarding wizard. Call this and then st.stop()
    until profile['onboarding_complete'] is True."""
    _init_state()

    st.markdown("""
    <div style="max-width:640px;margin:0 auto;">
        <div style="text-align:center;padding:8px 0 18px 0;">
            <div style="font-size:2rem;font-weight:800;font-family:'Sora',sans-serif;color:#0B1D51;">
                Welcome to Investor 360
            </div>
            <div style="color:#5a7199;font-size:0.95rem;margin-top:6px;">
                A few quick questions so we can tailor the platform to you.
                This only takes a minute, and we'll never ask again.
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    _progress_bar()
    st.write("")

    step = st.session_state.onboarding_step
    answers = st.session_state.onboarding_answers

    container = st.container()
    with container:
        if step == 0:
            st.markdown("### Have you invested in the Colombo Stock Exchange before?")
            choice = st.radio("Prior CSE experience", ["Yes", "No"], label_visibility="collapsed", key="q_experience")
            if st.button("Continue", type="primary"):
                answers["prior_cse_experience"] = choice
                _next_step()

        elif step == 1:
            st.markdown("### Do you already have a CDS account?")
            choice = st.radio("CDS account", ["Yes", "No"], label_visibility="collapsed", key="q_cds")
            if choice == "No":
                with st.expander("What is a CDS Account?", expanded=True):
                    st.markdown(
                        "A **Central Depository System (CDS) account** is the account that holds your "
                        "shares electronically once you buy them on the Colombo Stock Exchange - similar "
                        "to a bank account, but for shares instead of money. You need one before you can "
                        "place your first trade, and it's opened for you by a licensed stockbroker, "
                        "usually alongside a trading account."
                    )
                    b1, b2 = st.columns(2)
                    with b1:
                        if st.button("View Broker Guide"):
                            answers["_wants_broker_guide"] = True
                            answers["has_cds_account"] = choice
                            _next_step()
                    with b2:
                        if st.button("Skip"):
                            answers["has_cds_account"] = choice
                            _next_step()
            else:
                if st.button("Continue", type="primary"):
                    answers["has_cds_account"] = choice
                    _next_step()

        elif step == 2:
            st.markdown("### What type of investor are you?")
            choice = st.radio(
                "Investor type", ["Beginner", "Intermediate", "Experienced"],
                label_visibility="collapsed", key="q_type",
            )
            if st.button("Continue", type="primary"):
                answers["investor_type"] = choice
                _next_step()

        elif step == 3:
            st.markdown("### What's your investment goal?")
            choice = st.radio(
                "Investment goal",
                ["Long-term Growth", "Dividend Income", "Capital Appreciation", "Undecided"],
                label_visibility="collapsed", key="q_goal",
            )
            if st.button("Continue", type="primary"):
                answers["investment_goal"] = choice
                _next_step()

        elif step == 4:
            st.markdown("### What's your risk appetite?")
            choice = st.radio("Risk appetite", ["Low", "Medium", "High"], label_visibility="collapsed", key="q_risk")
            if st.button("Finish Setup", type="primary"):
                answers["risk_appetite"] = choice
                wants_broker_guide = answers.pop("_wants_broker_guide", False)
                mark_onboarding_complete(answers)
                st.session_state.pop("onboarding_step", None)
                st.session_state.pop("onboarding_answers", None)
                if wants_broker_guide:
                    st.session_state.pending_nav = "Getting Started"
                    st.session_state.pending_nav_tab = "Broker Comparison"
                st.session_state.just_onboarded = True
                st.rerun()

    st.write("")
    st.caption("You can change these answers anytime from Settings in the sidebar.")
