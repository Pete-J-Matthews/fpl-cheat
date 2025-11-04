"""
Rendering functions for displaying FPL team picks and player cards.
"""

import os
import base64
from typing import List, Dict, Optional

import streamlit as st

from app.fpl_api import FPL_HEADERS


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
def _b64_image(path: str) -> Optional[str]:
    """Convert image file to base64 string."""
    try:
        with open(path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return None


@st.cache_data(show_spinner=False)
def get_opponent_label(player_team_id: int, fixtures: List[Dict], team_lookup: Dict[int, Dict[str, str]]) -> str:
    """Get opponent label for a player's team in the current gameweek."""
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


def render_picks_table(picks: List[Dict], element_lookup: Dict[int, Dict[str, str]]):
    """Render picks as a simple table."""
    rows = [
        {
            "player": element_lookup.get(p.get("element"), {}).get("name", ""),
            "position": element_lookup.get(p.get("element"), {}).get("position", ""),
        }
        for p in picks
    ]
    order = {"GKP": 0, "DEF": 1, "MID": 2, "FWD": 3}
    rows.sort(key=lambda r: (order.get(r.get("position", ""), 99), r.get("player", "")))
    st.table(rows)


def _render_player_card(col, name: str, opp_label: str, team_code: str, is_captain: bool, is_vice: bool, team_short: Optional[str] = None):
    """Render a single player card with jersey image."""
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


def _render_player_row(picks: List[Dict], element_lookup: Dict[int, Dict[str, str]], team_lookup: Dict[int, Dict[str, str]], fixtures: List[Dict]):
    """Helper to render a row of players."""
    cols = st.columns(len(picks))
    for idx, p in enumerate(picks):
        el = int(p.get("element"))
        meta = element_lookup.get(el, {})
        team_id = int(meta.get("team_id", 0))
        team_code = team_lookup.get(team_id, {}).get("code", "")
        name = meta.get("name", "")
        opp = get_opponent_label(team_id, fixtures, team_lookup)
        team_short = team_lookup.get(team_id, {}).get("short_name", "")
        _render_player_card(cols[idx], name, opp, str(team_code), bool(p.get("is_captain")), bool(p.get("is_vice_captain")), team_short)


def render_pitch(picks: List[Dict], element_lookup: Dict[int, Dict[str, str]], team_lookup: Dict[int, Dict[str, str]], fixtures: List[Dict], show_bench: bool = True):
    """Render team picks in a pitch formation layout."""
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
        if row:
            _render_player_row(row, element_lookup, team_lookup, fixtures)

    if show_bench and bench:
        st.write("")
        st.subheader("Bench")
        _render_player_row(bench, element_lookup, team_lookup, fixtures)

