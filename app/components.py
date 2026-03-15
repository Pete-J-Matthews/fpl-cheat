"""
UI components for the FPL Cheat app.
"""

from typing import Dict, List, Optional

import streamlit as st

from app.cache import get_current_event_id_cached
from app.comparison import find_top_similar_teams
from app.database import get_creator_teams, search_managers


def manager_searchbox_options(searchterm: str) -> list[tuple[str, int]]:
    """
    Search function for streamlit-searchbox. Returns options as (display_text, manager_id)
    so the selected value is the manager_id. Call with 3+ chars for name/team search,
    or digits only for manager ID lookup.
    """
    term = (searchterm or "").strip()
    if not term:
        return []
    # Manager ID (digits only): single option that returns the id
    if term.isdigit():
        return [(f"Manager ID {term}", int(term))]
    # Name/team search: require 3+ characters before showing dropdown options
    if len(term) < 3:
        return []
    try:
        matches = search_managers(term)
        return [
            (f"{m['manager_name']} — {m['team_name']} (id {m['manager_id']})", m["manager_id"])
            for m in matches
        ]
    except Exception:
        return []


def process_manager_search(q: str, current_manager_id: int | None) -> tuple[int | None, list[dict]]:
    """
    Process manager search query. Returns (manager_id, matches).
    - Numeric ID: sets manager_id and returns (manager_id, []).
    - Text search with matches: returns (current_manager_id, matches); caller must show
      dropdown and set manager_id from selection (no auto-select for single match).
    - No matches / short query: returns (manager_id, []) and may show info/error messages.
    """
    if "manager_id" not in st.session_state:
        st.session_state.manager_id = None

    manager_id = current_manager_id or st.session_state.manager_id

    # Direct manager ID (numbers only): set and return, no dropdown
    if q and q.strip().isdigit():
        input_manager_id = int(q.strip())
        if st.session_state.manager_id != input_manager_id:
            st.session_state.manager_id = input_manager_id
            if "manager_selectbox" in st.session_state:
                del st.session_state["manager_selectbox"]
        return st.session_state.manager_id, []

    # Text search: require 3+ chars
    matches: list[dict] = []
    if q and q.strip():
        if len(q.strip()) >= 2:
            try:
                matches = search_managers(q)
            except Exception as e:
                st.error(f"⚠️ {str(e)}")
                matches = []
        else:
            st.info("💡 Enter at least 3 characters to search, or enter your manager ID (numbers only) directly")

    # When we have matches (1 or more), never auto-select; caller shows dropdown
    if matches:
        return manager_id, matches

    if q and len(q.strip()) >= 2:
        st.info("No matches found. Try a different search term or enter your manager ID directly (numbers only).")

    return manager_id, []


def get_manager_dropdown_options(matches: list[dict]) -> list[str]:
    """Return placeholder + option labels for the manager selectbox."""
    placeholder = "--- Select a manager ---"
    labels = [
        f"{m['manager_name']} — {m['team_name']} (id {m['manager_id']})"
        for m in matches
    ]
    return [placeholder] + labels


def get_manager_id_from_choice(choice: str, placeholder: str = "--- Select a manager ---") -> int | None:
    """Parse manager_id from selectbox choice string. Returns None if placeholder or parse fails."""
    if not choice or choice == placeholder:
        return None
    try:
        return int(choice.split("id ")[-1].strip(")"))
    except (ValueError, IndexError):
        return None


def _init_comparison_state() -> None:
    if "comparison_results" not in st.session_state:
        st.session_state.comparison_results = None
    if "selected_creator_team_id" not in st.session_state:
        st.session_state.selected_creator_team_id = None
    if "comparison_manager_id" not in st.session_state:
        st.session_state.comparison_manager_id = None


def run_compare_if_needed(
    user_picks: List[Dict],
    element_lookup: Dict[int, Dict[str, str]],
    current_gameweek: int,
    manager_id: Optional[int],
) -> None:
    """Run team comparison when a manager is selected. No button; runs automatically. No return."""
    _init_comparison_state()
    if not manager_id:
        return
    # Re-run comparison only when manager changed or we have no results yet
    if st.session_state.comparison_manager_id != manager_id or st.session_state.comparison_results is None:
        with st.spinner("Comparing teams..."):
            live_gameweek = get_current_event_id_cached()
            creator_teams = get_creator_teams()
            creator_teams = [t for t in creator_teams if t.get("current_gameweek") == live_gameweek]
            if not creator_teams:
                st.warning(f"No creator teams available for gameweek {live_gameweek}. Please update creator teams first.")
                st.session_state.comparison_results = None
            else:
                top_matches = find_top_similar_teams(user_picks, creator_teams, element_lookup, top_n=3)
                st.session_state.comparison_results = top_matches
                # Default to first (most similar) team so the first pill is selected immediately
                first_team = top_matches[0][0] if top_matches else None
                st.session_state.selected_creator_team_id = first_team.get("team_id") if first_team else None
            st.session_state.comparison_manager_id = manager_id


def _select_creator_team(team_id: int) -> None:
    """on_click callback: runs before the rest of the script, so pill highlight updates on first click."""
    st.session_state.selected_creator_team_id = team_id


def render_similar_teams() -> Optional[Dict]:
    """
    Render Similar Teams section (pills) if comparison results exist.
    Returns selected creator team dict or None.
    """
    _init_comparison_state()
    if not st.session_state.comparison_results:
        return None
    # If nothing selected yet, default to first (most similar) team so first pill is selected
    if st.session_state.selected_creator_team_id is None:
        first_team = st.session_state.comparison_results[0][0]
        st.session_state.selected_creator_team_id = first_team.get("team_id")
    with st.container(key="similar_teams_pills"):
        st.markdown("### Similar Teams")
        cols = st.columns(3)
        for idx, (creator_team, similarity) in enumerate(st.session_state.comparison_results):
            team_id = creator_team.get("team_id")
            manager_name = creator_team.get("manager_name", f"Team {team_id}")
            with cols[idx]:
                button_type = "primary" if st.session_state.selected_creator_team_id == team_id else "secondary"
                st.button(
                    manager_name,
                    key=f"select_creator_{team_id}",
                    use_container_width=True,
                    type=button_type,
                    on_click=_select_creator_team,
                    args=(team_id,),
                )
                st.markdown(
                    f'<p class="similarity-label">{similarity}% similar</p>',
                    unsafe_allow_html=True,
                )
    selected_team_id = st.session_state.selected_creator_team_id
    if selected_team_id:
        for creator_team, _ in st.session_state.comparison_results:
            if creator_team.get("team_id") == selected_team_id:
                return creator_team
    return None


def render_compare_section(
    user_picks: List[Dict],
    element_lookup: Dict[int, Dict[str, str]],
    current_gameweek: int,
    manager_id: Optional[int] = None,
) -> Optional[Dict]:
    """
    Run comparison if needed and render comparison results (convenience: both in one call).
    Returns selected creator team dict if one is selected, None otherwise.
    """
    run_compare_if_needed(user_picks, element_lookup, current_gameweek, manager_id)
    return render_similar_teams()

