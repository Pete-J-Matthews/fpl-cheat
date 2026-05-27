import app.comparison as comparison


def test_extract_player_ids_from_picks():
    picks = [
        {"element": 1},
        {"element": "2"},
        {"element": None},
        {},
        {"element": 0},  # ignored because falsy
    ]
    assert comparison.extract_player_ids_from_picks(picks) == {1, 2}


def test_parse_creator_team_players_exact_match():
    element_lookup = {
        10: {"name": "Salah"},
        11: {"name": "Gabriel"},
    }
    creator_team = {
        "player_1": "Salah (MID) (C)",
        "player_2": "Gabriel (DEF)",
    }
    assert comparison.parse_creator_team_players(creator_team, element_lookup) == {
        10,
        11,
    }


def test_parse_creator_team_players_partial_match_via_prefix():
    # lookup_name="harry kane", name_part="Harry" -> second fallback matches because
    # lookup_name.startswith(name_part.lower()) is True.
    element_lookup = {
        20: {"name": "Harry Kane"},
    }
    creator_team = {
        "player_1": "Harry (FWD)",
    }
    assert comparison.parse_creator_team_players(creator_team, element_lookup) == {20}


def test_calculate_team_similarity_common_players():
    user_ids = {1, 2, 3}
    creator_ids = {2, 3, 4}
    # common=2, max_team_size=3 => 66.7
    assert comparison.calculate_team_similarity(user_ids, creator_ids) == 66.7


def test_calculate_team_similarity_handles_empty_sets():
    assert comparison.calculate_team_similarity(set(), {1, 2}) == 0.0
    assert comparison.calculate_team_similarity({1, 2}, set()) == 0.0


def test_find_top_similar_teams_sorts_and_limits():
    element_lookup = {
        1: {"name": "A"},
        2: {"name": "B"},
        3: {"name": "C"},
        4: {"name": "D"},
        5: {"name": "E"},
    }

    user_picks = [{"element": 1}, {"element": 2}, {"element": 3}]
    creator_teams = [
        {"manager_name": "team1", "player_1": "A (GKP)", "player_2": "B (DEF)", "player_3": "C (MID)"},
        {"manager_name": "team2", "player_1": "A (GKP)", "player_2": "D (DEF)", "player_3": "E (MID)"},
        {"manager_name": "team3", "player_1": "B (DEF)", "player_2": "C (MID)"},
    ]

    top = comparison.find_top_similar_teams(
        user_picks=user_picks,
        creator_teams=creator_teams,
        element_lookup=element_lookup,
        top_n=2,
    )

    assert len(top) == 2
    assert top[0][0]["manager_name"] == "team1"
    assert top[0][1] == 100.0

    assert top[1][0]["manager_name"] == "team3"
    # team3: {2,3} vs {1,2,3} => common=2, max_team_size=3 => 66.7
    assert top[1][1] == 66.7

