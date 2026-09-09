"""Cached data fetching functions for the FPL Cheat app."""

import streamlit as st

from app.database import get_creator_teams
from app.fpl_api import (
    build_element_lookup,
    fetch_bootstrap,
    fetch_entry_picks,
    get_current_event_id,
)


@st.cache_data(ttl=60)
def fetch_entry_picks_cached(manager_id: int, event_id: int) -> dict | None:
    """Cached wrapper for fetch_entry_picks."""
    data = fetch_entry_picks(manager_id, event_id)
    if not data:
        st.error(f"Failed to fetch picks for manager {manager_id}")
    return data


@st.cache_data(ttl=120)
def get_current_event_id_cached() -> int:
    """Cached wrapper for get_current_event_id."""
    return get_current_event_id()


@st.cache_resource(ttl=600)
def fetch_bootstrap_cached() -> dict | None:
    """Cached wrapper for fetch_bootstrap."""
    data = fetch_bootstrap()
    if not data:
        st.error("Failed to fetch bootstrap data")
    return data


@st.cache_data(ttl=300)
def get_creator_teams_cached() -> list:
    """Cached wrapper for get_creator_teams."""
    return get_creator_teams()


def build_lookups(
    bootstrap: dict,
) -> tuple[dict[int, dict[str, str]], dict[int, dict[str, str]]]:
    """Return (element_lookup, team_lookup).
    element_lookup[element_id] -> {name, position, team_id}
    team_lookup[team_id] -> {short_name, code}
    """
    element_lookup = build_element_lookup(bootstrap, include_team_id=True)
    team_lookup: dict[int, dict[str, str]] = {}
    for t in bootstrap.get("teams") or []:
        try:
            team_lookup[int(t["id"])] = {
                "short_name": str(t.get("short_name", "")),
                "code": str(t.get("code", "")),
            }
        except Exception:
            continue
    return element_lookup, team_lookup
