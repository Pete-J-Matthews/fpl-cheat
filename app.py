"""
Minimal Streamlit app: search manager → optional manual manager_id → fetch my-team → list picks.
Aligned with build_interface and fetch_data tickets.
"""

from typing import List, Dict, Optional, Tuple

import requests
import streamlit as st
import os
import base64

from database import search_managers


st.set_page_config(page_title="FPL Cheat", page_icon="favicon.png", layout="centered")

FPL_ENTRY_PICKS_URL = "https://fantasy.premierleague.com/api/entry/{manager_id}/event/{event_id}/picks/"
FPL_BOOTSTRAP_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"
FPL_FIXTURES_URL = "https://fantasy.premierleague.com/api/fixtures/"
FPL_HEADERS = {
    "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0 Safari/537.36",
    "Referer": "https://fantasy.premierleague.com/",
}


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
def fetch_bootstrap() -> Optional[Dict]:
    try:
        r = requests.get(FPL_BOOTSTRAP_URL, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"Failed to fetch bootstrap: {e}")
        return None


@st.cache_data(ttl=300)
def fetch_fixtures(event_id: int) -> List[Dict]:
    try:
        r = requests.get(FPL_FIXTURES_URL, params={"event": event_id}, timeout=10)
        r.raise_for_status()
        return r.json() or []
    except Exception as e:
        st.warning(f"Failed to fetch fixtures for GW {event_id}: {e}")
        return []


def build_lookups(bootstrap: Dict) -> Tuple[Dict[int, Dict[str, str]], Dict[int, Dict[str, str]]]:
    """Return (element_lookup, team_lookup).
    element_lookup[element_id] -> {name, position, team_id}
    team_lookup[team_id] -> {short_name, code}
    """
    element_lookup: Dict[int, Dict[str, str]] = {}
    team_lookup: Dict[int, Dict[str, str]] = {}

    elements = bootstrap.get("elements") or []
    teams = bootstrap.get("teams") or []
    positions = {1: "GKP", 2: "DEF", 3: "MID", 4: "FWD"}

    for t in teams:
        try:
            team_lookup[int(t["id"])]= {"short_name": str(t.get("short_name", "")), "code": str(t.get("code", ""))}
        except Exception:
            continue

    for e in elements:
        try:
            element_lookup[int(e["id"])]= {
                "name": str(e.get("web_name", "")),
                "position": positions.get(int(e.get("element_type", 0)), ""),
                "team_id": int(e.get("team", 0)),
            }
        except Exception:
            continue

    return element_lookup, team_lookup


def _download(url: str) -> Optional[bytes]:
    try:
        r = requests.get(url, timeout=10, headers=FPL_HEADERS, allow_redirects=True)
        if r.status_code == 200 and r.content:
            content_type = r.headers.get("Content-Type", "")
            if "image" in content_type or url.endswith(".png"):
                return r.content
    except Exception:
        pass
    return None


def ensure_shirt(team_code: str, team_short: Optional[str] = None) -> Optional[str]:
    """Return local jersey path from assets/jerseys; prefers {SHORT}.png then shirt_{code}.png."""
    base = os.path.join("assets", "jerseys")
    os.makedirs(base, exist_ok=True)
    if team_short:
        by_short = os.path.join(base, f"{str(team_short).upper()}.png")
        if os.path.exists(by_short):
            return by_short
    by_code = os.path.join(base, f"shirt_{team_code}.png")
    return by_code if os.path.exists(by_code) else None


@st.cache_data(show_spinner=False)
def get_opponent_label(player_team_id: int, fixtures: List[Dict], team_lookup: Dict[int, Dict[str, str]]) -> str:
    # Find fixture where this team plays; fixtures are already filtered to one GW
    for fx in fixtures:
        th = int(fx.get("team_h", 0))
        ta = int(fx.get("team_a", 0))
        if player_team_id == th:
            opp = team_lookup.get(ta, {}).get("short_name", "")
            return f"{opp} (H)" if opp else "H"
        if player_team_id == ta:
            opp = team_lookup.get(th, {}).get("short_name", "")
            return f"{opp} (A)" if opp else "A"
    # Could be blank GW; show just team short
    short = team_lookup.get(player_team_id, {}).get("short_name", "")
    return short

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


@st.cache_data(show_spinner=False)
def _b64_image(path: str) -> Optional[str]:
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return None


def _render_player_card(col, name: str, opp_label: str, team_code: str, is_captain: bool, is_vice: bool, team_short: Optional[str] = None):
    path = ensure_shirt(team_code, team_short)
    if path:
        b64 = _b64_image(path)
        if b64:
            col.markdown(
                f"""
                <div class="player-card">
                    <img src="data:image/png;base64,{b64}" alt="{name}" />
                </div>
                """,
                unsafe_allow_html=True,
            )
        else:
            col.markdown(
                f"<div class='player-card'>shirt {team_code}</div>",
                unsafe_allow_html=True,
            )
    else:
        # Placeholder box if image missing
        col.markdown(
            f"<div class='player-card'>shirt {team_code}</div>",
            unsafe_allow_html=True,
        )
    label = name
    if is_captain:
        label += " (C)"
    elif is_vice:
        label += " (V)"
    col.markdown(f"**{label}**")
    if opp_label:
        col.caption(opp_label)


def render_pitch(picks: List[Dict], element_lookup: Dict[int, Dict[str, str]], team_lookup: Dict[int, Dict[str, str]], fixtures: List[Dict], show_bench: bool = True):
    starters = [p for p in picks if int(p.get("multiplier", 0)) > 0 and int(p.get("position", 0)) <= 11]
    bench = sorted([p for p in picks if int(p.get("position", 0)) >= 12], key=lambda x: int(x.get("position", 0)))

    lines: Dict[str, List[Dict]] = {"GKP": [], "DEF": [], "MID": [], "FWD": []}
    for p in starters:
        el = int(p.get("element"))
        meta = element_lookup.get(el, {})
        pos = meta.get("position", "")
        lines.setdefault(pos, []).append(p)

    # Render each line in GKP->FWD order
    for pos in ["GKP", "DEF", "MID", "FWD"]:
        row = lines.get(pos, [])
        if not row:
            continue
        cols = st.columns(len(row))
        for idx, p in enumerate(row):
            el = int(p.get("element"))
            meta = element_lookup.get(el, {})
            team_id = int(meta.get("team_id", 0))
            team_code = team_lookup.get(team_id, {}).get("code", "")
            name = meta.get("name", "")
            opp = get_opponent_label(team_id, fixtures, team_lookup)
            team_short = team_lookup.get(team_id, {}).get("short_name", "")
            _render_player_card(cols[idx], name, opp, str(team_code), bool(p.get("is_captain")), bool(p.get("is_vice_captain")), team_short)

    if show_bench and bench:
        st.write("")
        st.subheader("Bench")
        cols = st.columns(len(bench))
        for idx, p in enumerate(bench):
            el = int(p.get("element"))
            meta = element_lookup.get(el, {})
            team_id = int(meta.get("team_id", 0))
            team_code = team_lookup.get(team_id, {}).get("code", "")
            name = meta.get("name", "")
            opp = get_opponent_label(team_id, fixtures, team_lookup)
            team_short = team_lookup.get(team_id, {}).get("short_name", "")
            _render_player_card(cols[idx], name, opp, str(team_code), bool(p.get("is_captain")), bool(p.get("is_vice_captain")), team_short)


def main():
    st.title("FPL Cheat")
    st.caption("Find your manager and view your current picks")
    # Add a pitch-like background behind the content (subtle stripes)
    st.markdown(
        """
        <style>
        .stApp {
            background: repeating-linear-gradient(
                0deg,
                #0b3e1d 0px,
                #0b3e1d 60px,
                #0e5226 60px,
                #0e5226 120px
            );
        }
        /* Constrain page width for better formation consistency */
        .block-container { max-width: 1100px; margin: 0 auto; }
        /* Player card styling: consistent size, centered, bordered */
        .player-card {
            width: 100%;
            max-width: 120px;
            margin: 0 auto 6px auto;
            padding: 8px 6px;
            border: 1px solid rgba(255,255,255,0.18);
            border-radius: 12px;
            background: rgba(0,0,0,0.08);
            backdrop-filter: blur(2px);
            text-align: center;
        }
        .player-card img {
            height: 80px; /* uniform shirt size */
            width: auto;
            display: block;
            margin: 0 auto;
        }
        /* Center player labels under shirts */
        .element-container p, .element-container div, .element-container span { text-align: center; }
        
        /* Give columns a little bottom spacing */
        [data-testid="column"] { padding-bottom: 10px; }
        /* Make player cards breathe a bit */
        [data-testid="column"] div:has(img) { padding-bottom: 4px; }
        </style>
        """,
        unsafe_allow_html=True,
    )

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
        bootstrap = fetch_bootstrap()
        if not bootstrap:
            st.error("Could not load bootstrap data.")
            return
        element_lookup, team_lookup = build_lookups(bootstrap)
        fixtures = fetch_fixtures(int(event_id))

        st.subheader("Your Team Picks")
        show_pitch = st.toggle("Pitch view", value=True)
        if show_pitch:
            render_pitch(picks, element_lookup, team_lookup, fixtures, show_bench=True)
        else:
            render_picks_table(picks)


if __name__ == "__main__":
    main()
