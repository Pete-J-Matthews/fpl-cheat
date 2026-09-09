"""Fetches current gameweek squads for content creator teams and stores them in PostgreSQL."""

import time

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

TEAM_INFO = {
    44: "Lets Talk FPL",
    200: "FPL Focal",
    1320: "FPL Harry",
    1587: "FPL Raptor",
    14501: "FPL Pickle",
    16267: "FPL Mate",
    6586: "Ben Crellin",
    441: "Az Phillips",
    1924811: "Kelly Somers",
    1514450: "Julien Laurens",
    260: "Sam Bonfield",
    341: "Lee Bonfield",
    135: "Holly Shand",
    7577129: "Ian Irwing",
    16725: "FPL Sonaldo",
    3570: "Pras",
    17614: "Gianni Buttice",
    963: "BigMan Bakar",
    251: "Yelena",
    698910: "Stormzy",
    2253812: "Chunkz",
    2869: "Fabio Borges",
    2140: "FPL Family",
    2974: "FPL Goat",
    1536: "FPL Hints",
    68585: "FPL Matthew",
    156: "FPL Salah",
    11539: "Jian Batra",
    24194: "Lateriser",
    9505: "Zophar",
    20360: "Andy Martin FPL",
}

CREATOR_TEAM_IDS = list(TEAM_INFO)
REQUEST_GAP = 0.5  # Seconds between FPL calls, to stay under its rate limit


def format_player(
    element_id: int, is_captain: bool, is_vice_captain: bool, lookup: dict
) -> str:
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
    return (
        manager.get("manager_name", f"Manager {team_id}")
        if manager
        else f"Manager {team_id}"
    )


def _result(
    success: int, failed: int, total: int, already_up_to_date: bool = False
) -> dict[str, int]:
    return {
        "success": success,
        "failed": failed,
        "total": total,
        "already_up_to_date": already_up_to_date,
    }


def update_all_creator_teams(progress_callback=None) -> dict[str, int]:
    """Fetch and store this gameweek's squad for every creator team."""
    progress = progress_callback or (lambda _message: None)
    total = len(CREATOR_TEAM_IDS)

    current_gw = get_current_event_id()
    progress(f"Checking current gameweek: {current_gw}")
    if get_current_creator_gameweek() == current_gw:
        return _result(0, 0, total, already_up_to_date=True)

    progress(f"Updating for gameweek {current_gw}...")
    bootstrap = fetch_bootstrap()
    if not bootstrap:
        progress("Error: Failed to fetch bootstrap data")
        return _result(0, total, total)

    element_lookup = build_element_lookup(bootstrap)
    success_count = failed_count = 0

    for idx, team_id in enumerate(CREATOR_TEAM_IDS, start=1):
        manager_name = get_manager_name(team_id)
        progress(f"Updating {idx}/{total}: {manager_name}")

        picks_data = fetch_entry_picks(team_id, current_gw)
        picks = (picks_data or {}).get("picks") or []
        if not picks:
            failed_count += 1
            time.sleep(REQUEST_GAP)
            continue

        team_data = {
            "team_id": team_id,
            "manager_name": manager_name,
            "current_gameweek": current_gw,
            **{f"player_{i}": None for i in range(1, 16)},
        }
        for pick in picks:
            slot = int(pick.get("position", 0))
            if 1 <= slot <= 15:
                team_data[f"player_{slot}"] = format_player(
                    int(pick.get("element", 0)),
                    bool(pick.get("is_captain", False)),
                    bool(pick.get("is_vice_captain", False)),
                    element_lookup,
                )

        if upsert_creator_team(team_data):
            success_count += 1
        else:
            failed_count += 1
        time.sleep(REQUEST_GAP)

    return _result(success_count, failed_count, total)
