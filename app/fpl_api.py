"""
Shared FPL API constants and utility functions.
"""

from typing import Dict, Optional

import requests

# FPL API Configuration
FPL_API_BASE = "https://fantasy.premierleague.com/api"
FPL_ENTRY_PICKS_URL = f"{FPL_API_BASE}/entry/{{manager_id}}/event/{{event_id}}/picks/"
FPL_BOOTSTRAP_URL = f"{FPL_API_BASE}/bootstrap-static/"
FPL_FIXTURES_URL = f"{FPL_API_BASE}/fixtures/"
FPL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Referer": "https://fantasy.premierleague.com/",
}

# Position mapping
POSITION_MAP = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}


def fetch_bootstrap() -> Optional[Dict]:
    """Fetch bootstrap data from FPL API."""
    try:
        r = requests.get(FPL_BOOTSTRAP_URL, timeout=10, headers=FPL_HEADERS)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return None


def get_current_event_id() -> int:
    """Get the current gameweek ID from FPL API."""
    try:
        r = requests.get(FPL_BOOTSTRAP_URL, timeout=10, headers=FPL_HEADERS)
        r.raise_for_status()
        data = r.json()
        events = data.get("events") or []
        for ev in events:
            if ev.get("is_current"):
                return int(ev.get("id", 1))
        # fallback to next or first
        for ev in events:
            if ev.get("is_next"):
                return int(ev.get("id", 1))
    except Exception: # Graceful fallback: return default gameweek 1 if API call fails
        pass
    return 1


def fetch_entry_picks(manager_id: int, event_id: int) -> Optional[Dict]:
    """Fetch picks for a manager for a specific gameweek."""
    try:
        resp = requests.get(
            FPL_ENTRY_PICKS_URL.format(manager_id=manager_id, event_id=event_id),
            timeout=10,
            headers=FPL_HEADERS,
        )
        resp.raise_for_status()
        return resp.json()
    except Exception:
        return None


def build_element_lookup(bootstrap: Dict, include_team_id: bool = False) -> Dict[int, Dict[str, str]]:
    """Build lookup dictionary for player elements.
    
    Args:
        bootstrap: Bootstrap data from FPL API
        include_team_id: If True, include team_id in the lookup
        
    Returns:
        element_lookup[element_id] -> {name, position[, team_id]}
    """
    element_lookup: Dict[int, Dict[str, str]] = {}
    elements = bootstrap.get("elements") or []

    for e in elements:
        try:
            data = {
                "name": str(e.get("web_name", "")),
                "position": POSITION_MAP.get(int(e.get("element_type", 0)), ""),
            }
            if include_team_id:
                data["team_id"] = int(e.get("team", 0))
            element_lookup[int(e["id"])] = data
        except Exception:
            continue

    return element_lookup

