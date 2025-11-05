"""
Team comparison logic for comparing user teams with creator teams.
"""

from typing import Dict, List, Set, Tuple


def extract_player_ids_from_picks(picks: List[Dict]) -> Set[int]:
    """Extract set of player element IDs from user picks."""
    player_ids = set()
    for pick in picks:
        element_id = pick.get("element")
        if element_id:
            player_ids.add(int(element_id))
    return player_ids


def parse_creator_team_players(creator_team: Dict, element_lookup: Dict[int, Dict[str, str]]) -> Set[int]:
    """
    Parse player_1 through player_15 strings to extract player names,
    then match to element IDs using element_lookup.
    
    Args:
        creator_team: Dict with player_1 through player_15 keys containing strings like "Salah (MID) (C)"
        element_lookup: Dict mapping element_id to {name, position, ...}
    
    Returns:
        Set of element IDs found in the creator team
    """
    player_ids = set()
    
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
        # Extract just the name part (everything before the first "(")
        name_part = player_str.split("(")[0].strip()
        if not name_part:
            continue
        
        # Try exact match first
        element_id = name_to_id.get(name_part.lower())
        if element_id:
            player_ids.add(element_id)
        else:
            # Try partial match (in case of variations)
            for lookup_name, lookup_id in name_to_id.items():
                if lookup_name.startswith(name_part.lower()) or name_part.lower().startswith(lookup_name):
                    player_ids.add(lookup_id)
                    break
    
    return player_ids


def calculate_team_similarity(user_player_ids: Set[int], creator_player_ids: Set[int]) -> float:
    """
    Calculate similarity score between two teams.
    
    Args:
        user_player_ids: Set of player element IDs from user team
        creator_player_ids: Set of player element IDs from creator team
    
    Returns:
        Similarity score as percentage (0.0 to 100.0)
    """
    if not user_player_ids or not creator_player_ids:
        return 0.0
    
    # Count common players
    common_players = len(user_player_ids & creator_player_ids)
    
    # Calculate percentage: common players / total unique players in both teams
    total_unique = len(user_player_ids | creator_player_ids)
    if total_unique == 0:
        return 0.0
    
    similarity = (common_players / total_unique) * 100.0
    
    return round(similarity, 1)


def find_top_similar_teams(
    user_picks: List[Dict],
    creator_teams: List[Dict],
    element_lookup: Dict[int, Dict[str, str]],
    top_n: int = 3
) -> List[Tuple[Dict, float]]:
    """
    Compare user team with all creator teams and return top N matches.
    
    Args:
        user_picks: List of pick dicts from user team
        creator_teams: List of creator team dicts from database
        element_lookup: Element lookup dict
        top_n: Number of top matches to return
    
    Returns:
        List of tuples: (creator_team_dict, similarity_score) sorted by similarity descending
    """
    # Extract user player IDs
    user_player_ids = extract_player_ids_from_picks(user_picks)
    
    if not user_player_ids:
        return []
    
    # Calculate similarity for each creator team
    similarities = []
    for creator_team in creator_teams:
        creator_player_ids = parse_creator_team_players(creator_team, element_lookup)
        similarity = calculate_team_similarity(user_player_ids, creator_player_ids)
        similarities.append((creator_team, similarity))
    
    # Sort by similarity descending
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # Return top N
    return similarities[:top_n]
