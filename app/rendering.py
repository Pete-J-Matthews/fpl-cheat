"""
Rendering functions for displaying FPL team picks and player cards.
"""

import os
import base64
from typing import List, Dict, Optional

import streamlit as st


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
    # Display fixture next to player name
    if opp_label:
        label += f" {opp_label}"
    col.markdown(f"**{label}**")


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


def creator_team_to_picks(creator_team: Dict, element_lookup: Dict[int, Dict[str, str]]) -> List[Dict]:
    """
    Convert creator team data (player_1 through player_15 strings) to picks format.
    
    Args:
        creator_team: Dict with player_1 through player_15 keys
        element_lookup: Element lookup dict
    
    Returns:
        List of pick dicts in format compatible with render_pitch
    """
    picks = []
    
    # Create reverse lookup: name -> element_id
    name_to_id = {}
    for element_id, data in element_lookup.items():
        name = data.get("name", "").strip()
        if name:
            name_to_id[name.lower()] = element_id
    
    # Parse each player string
    for i in range(1, 16):
        player_str = creator_team.get(f"player_{i}")
        if not player_str:
            continue
        
        # Parse format: "Name (POS)" or "Name (POS) (C)" or "Name (POS) (VC)"
        # Extract name (everything before first "(")
        name_part = player_str.split("(")[0].strip()
        if not name_part:
            continue
        
        # Extract position and captaincy
        is_captain = "(C)" in player_str
        is_vice_captain = "(VC)" in player_str
        
        # Find element ID
        element_id = None
        # Try exact match first
        element_id = name_to_id.get(name_part.lower())
        if not element_id:
            # Try partial match
            for lookup_name, lookup_id in name_to_id.items():
                if lookup_name.startswith(name_part.lower()) or name_part.lower().startswith(lookup_name):
                    element_id = lookup_id
                    break
        
        if element_id:
            # Create pick dict
            pick = {
                "element": element_id,
                "position": i,
                "multiplier": 1 if i <= 11 else 0,  # Starters have multiplier > 0
                "is_captain": is_captain,
                "is_vice_captain": is_vice_captain,
            }
            picks.append(pick)
    
    return picks


def render_pitch(picks: List[Dict], element_lookup: Dict[int, Dict[str, str]], team_lookup: Dict[int, Dict[str, str]], fixtures: List[Dict], show_bench: bool = True, title: Optional[str] = None):
    """Render team picks in a pitch formation layout.
    
    Args:
        picks: List of pick dicts
        element_lookup: Element lookup dict
        team_lookup: Team lookup dict
        fixtures: List of fixture dicts
        show_bench: Whether to show bench players
        title: Optional title to display above the pitch
    """
    if title:
        st.markdown(f"**{title}**")
    
    starters = [p for p in picks if int(p.get("multiplier", 0)) > 0 and int(p.get("position", 0)) <= 11]
    bench = sorted([p for p in picks if int(p.get("position", 0)) >= 12], key=lambda x: int(x.get("position", 0)))

    lines: Dict[str, List[Dict]] = {"GKP": [], "DEF": [], "MID": [], "FWD": []}
    for p in starters:
        el = int(p.get("element"))
        meta = element_lookup.get(el, {})
        pos = meta.get("position", "")
        lines.setdefault(pos, []).append(p)

    # Render each line in GKP->FWD order with reduced spacing
    for pos in ["GKP", "DEF", "MID", "FWD"]:
        row = lines.get(pos, [])
        if row:
            _render_player_row(row, element_lookup, team_lookup, fixtures)
            # Reduce spacing between rows
            st.markdown("<div style='margin-bottom: -0.5rem;'></div>", unsafe_allow_html=True)

    if show_bench and bench:
        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("**Bench:**")
        _render_player_row(bench, element_lookup, team_lookup, fixtures)

