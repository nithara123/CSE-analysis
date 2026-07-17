"""
preferences.py
--------------
Persistent storage for user onboarding answers / investor profile.

Streamlit's `st.session_state` is wiped every time the browser tab is
closed or the server restarts, so it cannot be used on its own to make
onboarding a "one-time-only" experience. This module backs it with a
small JSON file on disk (PREFS_PATH) so the profile survives restarts,
exactly like a lightweight user-preferences file.

If you deploy Investor360 with multiple concurrent users on one server
and want per-user (not per-installation) persistence, swap the file I/O
in this module for a row in a real database keyed by user id / cookie.
The rest of the app only talks to this module's functions, so that swap
never touches onboarding.py or app.py.
"""

import json
import os
from datetime import datetime

PREFS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".user_data")
PREFS_PATH = os.path.join(PREFS_DIR, "investor_profile.json")

DEFAULT_PROFILE = {
    "onboarding_complete": False,
    "prior_cse_experience": None,      # "Yes" / "No"
    "has_cds_account": None,           # "Yes" / "No"
    "investor_type": None,             # "Beginner" / "Intermediate" / "Experienced"
    "investment_goal": None,           # "Long-term Growth" / "Dividend Income" / "Capital Appreciation" / "Undecided"
    "risk_appetite": None,             # "Low" / "Medium" / "High"
    "wants_recommendations": None,     # "Yes" / "No"
    "completed_at": None,
}


def _ensure_dir():
    os.makedirs(PREFS_DIR, exist_ok=True)


def load_profile() -> dict:
    """Load the persisted investor profile, or return defaults if none exists yet."""
    _ensure_dir()
    if not os.path.exists(PREFS_PATH):
        return dict(DEFAULT_PROFILE)
    try:
        with open(PREFS_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
        profile = dict(DEFAULT_PROFILE)
        profile.update(saved)
        return profile
    except Exception:
        # Corrupted file - don't crash the app, just start fresh.
        return dict(DEFAULT_PROFILE)


def save_profile(profile: dict) -> None:
    """Persist the investor profile to disk."""
    _ensure_dir()
    with open(PREFS_PATH, "w", encoding="utf-8") as f:
        json.dump(profile, f, indent=2)


def mark_onboarding_complete(answers: dict) -> dict:
    """Merge onboarding answers into the profile, flag it complete, and persist."""
    profile = load_profile()
    profile.update(answers)
    profile["onboarding_complete"] = True
    profile["completed_at"] = datetime.now().isoformat(timespec="seconds")
    save_profile(profile)
    return profile


def reset_onboarding() -> dict:
    """Wipe the persisted profile so onboarding will show again on next load."""
    profile = dict(DEFAULT_PROFILE)
    save_profile(profile)
    return profile
