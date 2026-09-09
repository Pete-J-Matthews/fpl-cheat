"""Team comparison logic for comparing user teams with creator teams."""

from collections.abc import Iterator


def iter_creator_players(
    creator_team: dict, element_lookup: dict[int, dict[str, str]]
) -> Iterator[tuple[int, int, bool, bool]]:
    """Yield (slot, element_id, is_captain, is_vice) for each "Name (POS) (C)" entry."""
    name_to_id: dict[str, int] = {}
    for element_id, data in element_lookup.items():
        name = data.get("name", "").strip().lower()
        if name:
            name_to_id[name] = element_id

    for slot in range(1, 16):
        entry = creator_team.get(f"player_{slot}") or ""
        name = entry.split("(")[0].strip().lower()
        if not name:
            continue
        # Exact match, else the first name that prefixes it either way (handles variations).
        element_id = name_to_id.get(name) or next(
            (
                i
                for n, i in name_to_id.items()
                if n.startswith(name) or name.startswith(n)
            ),
            None,
        )
        if element_id:
            yield slot, element_id, "(C)" in entry, "(VC)" in entry


def extract_player_ids_from_picks(picks: list[dict]) -> set[int]:
    """Extract set of player element IDs from user picks."""
    return {int(p["element"]) for p in picks if p.get("element")}


def parse_creator_team_players(
    creator_team: dict, element_lookup: dict[int, dict[str, str]]
) -> set[int]:
    """Element IDs of the players named in a creator team's player_1..player_15 strings."""
    return {eid for _, eid, _, _ in iter_creator_players(creator_team, element_lookup)}


def calculate_team_similarity(
    user_player_ids: set[int], creator_player_ids: set[int]
) -> float:
    """Percentage of the larger squad that both teams share. max() avoids inflating a partial parse."""
    if not user_player_ids or not creator_player_ids:
        return 0.0
    common = len(user_player_ids & creator_player_ids)
    return round(common / max(len(user_player_ids), len(creator_player_ids)) * 100.0, 1)


def find_top_similar_teams(
    user_picks: list[dict],
    creator_teams: list[dict],
    element_lookup: dict[int, dict[str, str]],
    top_n: int = 3,
) -> list[tuple[dict, float]]:
    """Top N (creator_team, similarity) pairs, most similar first."""
    user_player_ids = extract_player_ids_from_picks(user_picks)
    if not user_player_ids:
        return []
    similarities = [
        (
            team,
            calculate_team_similarity(
                user_player_ids, parse_creator_team_players(team, element_lookup)
            ),
        )
        for team in creator_teams
    ]
    similarities.sort(key=lambda pair: pair[1], reverse=True)
    return similarities[:top_n]
