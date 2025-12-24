"""Fetches current gameweek squads for content creator teams and stores them in PostgreSQL."""

import time
from typing import Dict, List

from app.database import (
    get_current_creator_gameweek,
    get_manager_by_id,
    upsert_creator_team,
)
from app.fpl_api import (
    build_element_lookup,
    fetch_bootstrap,
    fetch_entry_picks,
    get_current_event_id,
)

CREATOR_TEAM_IDS = [44, 200, 1320, 1587, 14501, 16267, 6586, 441, 1924811, 1514450, 260, 341, 135, 7577129, 16725, 3570, 17614, 963, 251, 698910, 2253812]

TEAM_INFO = {
    44: 'Lets Talk FPL', 200: 'FPL Focal', 1320: 'FPL Harry', 1587: 'FPL Raptor',
    14501: 'FPL Pickle', 16267: 'FPL Mate', 6586: 'Ben Crellin', 441: 'Az Phillips',
    1924811: 'Kelly Somers', 1514450: 'Julien Laurens', 260: 'Sam Bonfield',
    341: 'Lee Bonfield', 135: 'Holly Shand', 7577129: 'Ian Irwing', 16725: 'FPL Sonaldo',
    3570: 'Pras', 17614: 'Gianni Buttice', 963: 'BigMan Bakar', 251: 'Yelena',
    698910: 'Stormzy', 2253812: 'Chunkz',
}


def format_player(element_id: int, is_captain: bool, is_vice_captain: bool, lookup: Dict) -> str:
    """Format player as 'Name (POS)' with optional '(C)' or '(VC)'."""
    data = lookup.get(element_id, {})
    name = data.get("name", "Unknown")
    pos = data.get("position", "")
    suffix = " (C)" if is_captain else " (VC)" if is_vice_captain else ""
    return f"{name} ({pos}){suffix}"


def get_manager_name(team_id: int) -> str:
    """Get manager name from TEAM_INFO or database."""
    if team_id in TEAM_INFO:
        return TEAM_INFO[team_id]
    manager = get_manager_by_id(team_id)
    return manager.get("manager_name", f"Manager {team_id}") if manager else f"Manager {team_id}"


def update_all_creator_teams(progress_callback=None) -> Dict[str, int]:
    """Update all creator teams using CREATOR_TEAM_IDS."""
    return update_creator_teams(CREATOR_TEAM_IDS, progress_callback)


def update_creator_teams(creator_team_ids: List[int], progress_callback=None) -> Dict[str, int]:
    """Update creator teams in the database."""
    if not creator_team_ids:
        return {"success": 0, "failed": 0, "total": 0, "already_up_to_date": False}

    current_gw = get_current_event_id()
    if progress_callback:
        progress_callback(f"Checking current gameweek: {current_gw}")
    
    if get_current_creator_gameweek() == current_gw:
        return {"success": 0, "failed": 0, "total": len(creator_team_ids), "already_up_to_date": True}
    
    if progress_callback:
        progress_callback(f"Updating for gameweek {current_gw}...")

    bootstrap = fetch_bootstrap()
    if not bootstrap:
        if progress_callback:
            progress_callback("Error: Failed to fetch bootstrap data")
        return {"success": 0, "failed": len(creator_team_ids), "total": len(creator_team_ids)}

    element_lookup = build_element_lookup(bootstrap)
    success_count = failed_count = 0

    for idx, team_id in enumerate(creator_team_ids):
        manager_name = get_manager_name(team_id)
        if progress_callback:
            progress_callback(f"Updating {idx + 1}/{len(creator_team_ids)}: {manager_name}")

        picks_data = fetch_entry_picks(team_id, current_gw)
        picks = picks_data.get("picks") if picks_data else []
        if not picks:
            failed_count += 1
            time.sleep(0.5)
            continue

        team_data = {
            "team_id": team_id,
            "manager_name": manager_name,
            "current_gameweek": current_gw,
            **{f"player_{i}": None for i in range(1, 16)}
        }

        for pick in picks:
            pos = int(pick.get("position", 0))
            if 1 <= pos <= 15:
                team_data[f"player_{pos}"] = format_player(
                    int(pick.get("element", 0)),
                    bool(pick.get("is_captain", False)),
                    bool(pick.get("is_vice_captain", False)),
                    element_lookup
                )

        if upsert_creator_team(team_data):
            success_count += 1
        else:
            failed_count += 1
        time.sleep(0.5)

    return {"success": success_count, "failed": failed_count, "total": len(creator_team_ids), "already_up_to_date": False}
