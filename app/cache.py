"""
Cached data fetching functions for the FPL Cheat app.
"""

from typing import Dict, List, Optional

import requests
import streamlit as st

from app.fpl_api import (
    FPL_FIXTURES_URL,
    FPL_HEADERS,
    fetch_bootstrap,
    fetch_entry_picks,
    get_current_event_id,
)


@st.cache_data(ttl=60)
def fetch_entry_picks_cached(manager_id: int, event_id: int) -> Optional[Dict]:
    """Cached wrapper for fetch_entry_picks."""
    data = fetch_entry_picks(manager_id, event_id)
    if not data:
        st.error(f"Failed to fetch picks for manager {manager_id}")
    return data


@st.cache_data(ttl=120)
def get_current_event_id_cached() -> int:
    """Cached wrapper for get_current_event_id."""
    return get_current_event_id()


@st.cache_data(ttl=600)
def fetch_bootstrap_cached() -> Optional[Dict]:
    """Cached wrapper for fetch_bootstrap."""
    data = fetch_bootstrap()
    if not data:
        st.error("Failed to fetch bootstrap data")
    return data


@st.cache_data(ttl=300)
def fetch_fixtures(event_id: int) -> List[Dict]:
    """Fetch fixtures for a specific gameweek."""
    try:
        r = requests.get(FPL_FIXTURES_URL, params={"event": event_id}, timeout=10)
        r.raise_for_status()
        return r.json() or []
    except Exception as e:
        st.warning(f"Failed to fetch fixtures for GW {event_id}: {e}")
        return []


def build_lookups(bootstrap: Dict) -> tuple[Dict[int, Dict[str, str]], Dict[int, Dict[str, str]]]:
    """Return (element_lookup, team_lookup).
    element_lookup[element_id] -> {name, position, team_id}
    team_lookup[team_id] -> {short_name, code}
    """
    from app.fpl_api import build_element_lookup
    
    element_lookup = build_element_lookup(bootstrap, include_team_id=True)
    team_lookup: Dict[int, Dict[str, str]] = {}
    teams = bootstrap.get("teams") or []

    for t in teams:
        try:
            team_lookup[int(t["id"])] = {"short_name": str(t.get("short_name", "")), "code": str(t.get("code", ""))}
        except Exception:
            continue

    return element_lookup, team_lookup

