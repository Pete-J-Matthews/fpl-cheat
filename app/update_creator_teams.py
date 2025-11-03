"""
Update Creator Teams Script

Fetches current gameweek squads for content creator teams from the FPL API
and stores them in the Supabase creator_teams table.
"""

import time
from typing import Dict, List

import streamlit as st

from app.database import get_client, upsert_creator_team, get_current_creator_gameweek
from app.fpl_api import (
    build_element_lookup,
    fetch_bootstrap,
    fetch_entry_picks,
    get_current_event_id,
)

# Creator team IDs - content creator FPL team IDs
CREATOR_TEAM_IDS: List[int] = [
    44,
    200,
    1320,
    1587,
    14501,
    16267,
    6586,
    441,
    1924811,
    1514450,
    260,
    341,
    135,
    7577129,
    16725,
    3570,
    17614,
    963,
    251,
    698910,
    2253812,
]

# Team information mapping - manually curated from FPL API
TEAM_INFO: Dict[int, Dict[str, str]] = {
    44: {'manager_name': 'Lets Talk FPL'},
    200: {'manager_name': 'FPL Focal'},
    1320: {'manager_name': 'FPL Harry'},
    1587: {'manager_name': 'FPL Raptor'},
    14501: {'manager_name': 'FPL Pickle'},
    16267: {'manager_name': 'FPL Mate'},
    6586: {'manager_name': 'Ben Crellin'},
    441: {'manager_name': 'Az Phillips'},
    1924811: {'manager_name': 'Kelly Somers'},
    1514450: {'manager_name': 'Julien Laurens'},
    260: {'manager_name': 'Sam Bonfield'},
    341: {'manager_name': 'Lee Bonfield'},
    135: {'manager_name': 'Holly Shand'},
    7577129: {'manager_name': 'Ian Irwing'},
    16725: {'manager_name': 'FPL Sonaldo'},
    3570: {'manager_name': 'Pras'},
    17614: {'manager_name': 'Gianni Buttice'},
    963: {'manager_name': 'BigMan Bakar'},
    251: {'manager_name': 'Yelena'},
    698910: {'manager_name': 'Stormzy'},
    2253812: {'manager_name': 'Chunkz'},
}






def format_player_string(
    element_id: int,
    position: int,
    is_captain: bool,
    is_vice_captain: bool,
    element_lookup: Dict[int, Dict[str, str]],
) -> str:
    """Format player string as 'Name (POS)' with optional '(C)' or '(VC)'."""
    element_data = element_lookup.get(element_id, {})
    name = element_data.get("name", "Unknown")
    pos = element_data.get("position", "")

    formatted = f"{name} ({pos})"
    if is_captain:
        formatted += " (C)"
    elif is_vice_captain:
        formatted += " (VC)"

    return formatted


def get_manager_info(team_id: int) -> Dict[str, str]:
    """Get manager_name from TEAM_INFO dictionary."""
    # First try to get from hardcoded TEAM_INFO
    if team_id in TEAM_INFO:
        return TEAM_INFO[team_id]
    
    # Fallback: try to get from all_managers table
    try:
        client = get_client()
        resp = (
            client.table("all_managers")
            .select("manager_id,manager_name")
            .eq("manager_id", team_id)
            .limit(1)
            .execute()
        )
        if resp.data and len(resp.data) > 0:
            return {
                "manager_name": resp.data[0].get("manager_name", ""),
            }
    except Exception as e:
        if st:
            st.debug(f"Could not fetch manager info for {team_id}: {e}")

    # Final fallback: return default name if not found
    return {"manager_name": f"Manager {team_id}"}


def update_all_creator_teams(progress_callback=None) -> Dict[str, int]:
    """Update all creator teams using the CREATOR_TEAM_IDS list."""
    return update_creator_teams(CREATOR_TEAM_IDS, progress_callback=progress_callback)


def update_creator_teams(creator_team_ids: List[int], progress_callback=None) -> Dict[str, int]:
    """
    Update creator teams in the database.
    
    Args:
        creator_team_ids: List of FPL team IDs to update
        progress_callback: Optional function to call with progress updates
        
    Returns:
        Dict with 'success' and 'failed' counts
    """
    if not creator_team_ids:
        return {"success": 0, "failed": 0, "total": 0, "already_up_to_date": False}

    # Fetch current gameweek
    current_gw = get_current_event_id()
    if progress_callback:
        progress_callback(f"Checking current gameweek: {current_gw}")
    
    # Check if teams are already up to date
    db_gameweek = get_current_creator_gameweek()
    if db_gameweek is not None and db_gameweek == current_gw:
        return {"success": 0, "failed": 0, "total": len(creator_team_ids), "already_up_to_date": True}
    
    if progress_callback:
        progress_callback(f"Updating for gameweek {current_gw}...")

    # Fetch bootstrap data once
    bootstrap = fetch_bootstrap()
    if not bootstrap:
        if progress_callback:
            progress_callback("Error: Failed to fetch bootstrap data")
        return {"success": 0, "failed": len(creator_team_ids), "total": len(creator_team_ids)}

    element_lookup = build_element_lookup(bootstrap)

    success_count = 0
    failed_count = 0

    for idx, team_id in enumerate(creator_team_ids):
        # Get manager info for display
        manager_info = get_manager_info(team_id)
        manager_name = manager_info.get("manager_name", f"Team {team_id}")
        
        if progress_callback:
            progress_callback(f"Updating {idx + 1}/{len(creator_team_ids)}: {manager_name}")

        # Fetch picks for this team
        picks_data = fetch_entry_picks(team_id, current_gw)
        if not picks_data:
            failed_count += 1
            time.sleep(0.5)  # Rate limiting
            continue

        picks = picks_data.get("picks") or []
        if not picks:
            failed_count += 1
            time.sleep(0.5)
            continue

        # Manager info already fetched above for display

        # Build team data structure
        team_data = {
            "team_id": team_id,
            "manager_name": manager_info["manager_name"],
            "current_gameweek": current_gw,
        }

        # Initialize all player columns
        for i in range(1, 16):
            team_data[f"player_{i}"] = None

        # Process picks and store in correct position slots
        for pick in picks:
            position = int(pick.get("position", 0))
            if position < 1 or position > 15:
                continue

            element_id = int(pick.get("element", 0))
            is_captain = bool(pick.get("is_captain", False))
            is_vice_captain = bool(pick.get("is_vice_captain", False))

            formatted_player = format_player_string(
                element_id, position, is_captain, is_vice_captain, element_lookup
            )

            team_data[f"player_{position}"] = formatted_player

        # Upsert to database
        if upsert_creator_team(team_data):
            success_count += 1
        else:
            failed_count += 1

        # Rate limiting
        time.sleep(0.5)

    return {
        "success": success_count,
        "failed": failed_count,
        "total": len(creator_team_ids),
        "already_up_to_date": False,
    }

