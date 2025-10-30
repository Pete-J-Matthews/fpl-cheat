"""
Minimal Streamlit app: search manager → optional manual manager_id → fetch my-team → list picks.
Aligned with build_interface and fetch_data tickets.
"""

from typing import List, Dict, Optional

import requests
import streamlit as st

from database import search_managers


st.set_page_config(page_title="FPL Cheat", page_icon="favicon.png", layout="centered")

FPL_ENTRY_PICKS_URL = "https://fantasy.premierleague.com/api/entry/{manager_id}/event/{event_id}/picks/"
FPL_BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"


@st.cache_data(ttl=60)
def fetch_entry_picks(manager_id: int, event_id: int) -> Optional[Dict]:
    try:
        resp = requests.get(
            FPL_ENTRY_PICKS_URL.format(manager_id=manager_id, event_id=event_id), timeout=10
        )
        resp.raise_for_status()
        return resp.json()
    except Exception as e:
        st.error(f"Failed to fetch picks: {e}")
        return None


@st.cache_data(ttl=120)
def get_current_event_id() -> int:
    try:
        r = requests.get(FPL_BOOTSTRAP_URL, timeout=10)
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
    except Exception:
        pass
    return 1


@st.cache_data(ttl=600)
def load_player_lookup() -> Dict[int, Dict[str, str]]:
    """Load players.csv if present and return element -> {name, position}."""
    try:
        import pandas as pd
        df = pd.read_csv("data/players.csv")
        mapping: Dict[int, Dict[str, str]] = {}
        for _, row in df.iterrows():
            try:
                mapping[int(row["element"])] = {
                    "name": str(row.get("web_name", "")),
                    "position": str(row.get("position", "")),
                }
            except Exception:
                continue
        return mapping
    except Exception:
        return {}


def render_picks_table(picks: List[Dict]):
    lookup = load_player_lookup()
    rows = [
        {
            "player": lookup.get(p.get("element"), {}).get("name", ""),
            "position": lookup.get(p.get("element"), {}).get("position", ""),
        }
        for p in picks
    ]
    order = {"GKP": 0, "DEF": 1, "MID": 2, "FWD": 3}
    rows.sort(key=lambda r: (order.get(r.get("position", ""), 99), r.get("player", "")))
    st.table(rows)


def main():
    st.title("FPL Cheat")
    st.caption("Find your manager and view your current picks")

    # Search by name
    q = st.text_input("Team or Manager name", placeholder="e.g., John or United")
    manager_id: Optional[int] = None

    if q:
        try:
            matches = search_managers(q)
        except Exception as e:
            st.error(f"Database error: {e}")
            matches = []

        if matches:
            labels = [
                f"{m['manager_name']} — {m['team_name']} (id {m['manager_id']})"
                for m in matches
            ]
            st.write("Select your manager:")
            choice = st.radio("", labels, index=0)
            if choice:
                # extract id from label
                manager_id = int(choice.split("id ")[-1].strip(")"))
        else:
            st.info("No matches found. You can enter your manager_id manually below.")

    # Manual manager_id
    if manager_id is None:
        manual = st.checkbox("Enter manager_id manually")
        if manual or q:
            val = st.text_input("manager_id", placeholder="e.g., 123456")
            if val.isdigit():
                manager_id = int(val)

    # Fetch and render picks
    if manager_id:
        default_gw = get_current_event_id()
        event_id = st.number_input("Gameweek", min_value=1, max_value=38, value=default_gw, step=1)
        with st.spinner("Fetching your team picks..."):
            data = fetch_entry_picks(manager_id, int(event_id))
        if not data:
            return
        picks = data.get("picks") or []
        if not picks:
            st.warning("No picks found.")
            return
        st.subheader("Your Team Picks")
        render_picks_table(picks)


if __name__ == "__main__":
    main()
