"""UI components for the FPL Cheat app."""

import streamlit as st

from app.cache import get_creator_teams_cached, get_current_event_id_cached
from app.comparison import find_top_similar_teams
from app.database import search_managers

STATE_DEFAULTS = {
    "comparison_results": None,
    "selected_creator_team_id": None,
    "comparison_manager_id": None,
}


def manager_searchbox_options(searchterm: str) -> list[tuple[str, int]]:
    """streamlit-searchbox options as (display_text, manager_id): digits are an ID, 3+ chars a name search."""
    term = (searchterm or "").strip()
    if not term:
        return []
    if term.isdigit():
        return [(f"Manager ID {term}", int(term))]
    if len(term) < 3:
        return []
    try:
        return [
            (
                f"{m['manager_name']} — {m['team_name']} (id {m['manager_id']})",
                m["manager_id"],
            )
            for m in search_managers(term)
        ]
    except Exception:
        return []


def _init_comparison_state() -> None:
    for key, default in STATE_DEFAULTS.items():
        st.session_state.setdefault(key, default)


def run_compare_if_needed(
    user_picks: list[dict],
    element_lookup: dict[int, dict[str, str]],
    manager_id: int | None,
) -> None:
    """Compare the user's team against creator teams, unless the current results already cover it."""
    _init_comparison_state()
    if not manager_id:
        return
    if (
        st.session_state.comparison_manager_id == manager_id
        and st.session_state.comparison_results is not None
    ):
        return

    with st.spinner("Comparing teams..."):
        live_gameweek = get_current_event_id_cached()
        creator_teams = [
            t
            for t in get_creator_teams_cached()
            if t.get("current_gameweek") == live_gameweek
        ]
        if not creator_teams:
            st.warning(
                f"No creator teams available for gameweek {live_gameweek}. Please update creator teams first."
            )
            st.session_state.comparison_results = None
        else:
            top_matches = find_top_similar_teams(
                user_picks, creator_teams, element_lookup, top_n=3
            )
            st.session_state.comparison_results = top_matches
            # Default to the most similar team so the first pill starts selected
            first_team = top_matches[0][0] if top_matches else None
            st.session_state.selected_creator_team_id = (
                first_team.get("team_id") if first_team else None
            )
        st.session_state.comparison_manager_id = manager_id


def _select_creator_team(team_id: int) -> None:
    """on_click callback: runs before the rest of the script, so pill highlight updates on first click."""
    st.session_state.selected_creator_team_id = team_id


def render_similar_teams() -> dict | None:
    """Render the Similar Teams pills and return the selected creator team, if any."""
    _init_comparison_state()
    results = st.session_state.comparison_results
    if not results:
        return None
    if st.session_state.selected_creator_team_id is None:
        st.session_state.selected_creator_team_id = results[0][0].get("team_id")

    with st.container(key="similar_teams_pills"):
        st.markdown("### Similar Teams")
        cols = st.columns(3)
        for col, (creator_team, similarity) in zip(cols, results, strict=False):
            team_id = creator_team.get("team_id")
            with col:
                st.button(
                    creator_team.get("manager_name", f"Team {team_id}"),
                    key=f"select_creator_{team_id}",
                    use_container_width=True,
                    type=(
                        "primary"
                        if st.session_state.selected_creator_team_id == team_id
                        else "secondary"
                    ),
                    on_click=_select_creator_team,
                    args=(team_id,),
                )
                st.markdown(
                    f'<p class="similarity-label">{similarity}% similar</p>',
                    unsafe_allow_html=True,
                )

    return next(
        (
            team
            for team, _ in results
            if team.get("team_id") == st.session_state.selected_creator_team_id
        ),
        None,
    )
