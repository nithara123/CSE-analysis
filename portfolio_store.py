"""
portfolio_store.py
-------------------
Lightweight persistence for the user's Portfolio / Watchlist, mirroring
preferences.py's pattern (JSON file on disk + session_state cache). This
keeps "Add to Portfolio" clicks on the Discover Companies page durable
across a server restart, without requiring a real database.
"""

import json
import os

STORE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".user_data")
STORE_PATH = os.path.join(STORE_DIR, "portfolio.json")


def _ensure_dir():
    os.makedirs(STORE_DIR, exist_ok=True)


def load_portfolio() -> list:
    _ensure_dir()
    if not os.path.exists(STORE_PATH):
        return []
    try:
        with open(STORE_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception:
        return []


def save_portfolio(company_names: list) -> None:
    _ensure_dir()
    with open(STORE_PATH, "w", encoding="utf-8") as f:
        json.dump(sorted(set(company_names)), f, indent=2)


def add_company(company_name: str) -> list:
    port = load_portfolio()
    if company_name not in port:
        port.append(company_name)
        save_portfolio(port)
    return port


def remove_company(company_name: str) -> list:
    port = load_portfolio()
    port = [c for c in port if c != company_name]
    save_portfolio(port)
    return port
