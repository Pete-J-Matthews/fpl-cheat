"""
UI components for the FPL Cheat app.
"""

from typing import Dict, List, Optional

import streamlit as st

from app.cache import get_current_event_id_cached
from app.comparison import find_top_similar_teams
from app.database import get_creator_teams, search_managers


def process_manager_search(q: str, current_manager_id: int | None) -> int | None:
    """Process manager search query and return manager_id."""
    if "manager_id" not in st.session_state:
        st.session_state.manager_id = None
    
    manager_id = current_manager_id or st.session_state.manager_id
    
    # Check if input is a manager_id (integer)
    if q and q.strip().isdigit():
        input_manager_id = int(q.strip())
        if st.session_state.manager_id != input_manager_id:
            st.session_state.manager_id = input_manager_id
            if "manager_selectbox" in st.session_state:
                del st.session_state["manager_selectbox"]
            return input_manager_id

    # Fetch matches when there's a query (only if not already using manager_id)
    matches = []
    if q and q.strip():
        # Only search if query is long enough (4+ characters)
        if len(q.strip()) >= 4:
            try:
                matches = search_managers(q)
            except Exception as e:
                error_msg = str(e)
                st.error(f"⚠️ {error_msg}")
                matches = []
        elif len(q.strip()) > 0:
            # Show helpful message for short queries
            st.info("💡 Enter at least 4 characters to search, or enter your manager ID (numbers only) directly")

    # Handle matches
    if matches:
        if len(matches) == 1:
            # Auto-select if only one match
            if manager_id != matches[0]["manager_id"]:
                manager_id = matches[0]["manager_id"]
                st.session_state.manager_id = manager_id
        else:
            # Show dropdown for multiple matches
            placeholder = "--- Select a manager ---"
            labels = [placeholder] + [
                f"{m['manager_name']} — {m['team_name']} (id {m['manager_id']})"
                for m in matches
            ]
            
            # Find current selection index
            current_index = 0
            if manager_id:
                for idx, m in enumerate(matches):
                    if m['manager_id'] == manager_id:
                        current_index = idx + 1
                        break
                if current_index == 0 and manager_id:
                    st.session_state.manager_id = None
                    manager_id = None
                    current_index = 0
            
            selectbox_key = "manager_selectbox"
            choice = st.selectbox(
                "Select manager:", 
                labels, 
                index=current_index,
                key=selectbox_key,
                label_visibility="visible"
            )
            
            if choice and choice != placeholder:
                try:
                    selected_id = int(choice.split("id ")[-1].strip(")"))
                    if st.session_state.manager_id != selected_id:
                        st.session_state.manager_id = selected_id
                        manager_id = selected_id
                except (ValueError, IndexError):
                    pass
            elif choice == placeholder:
                if st.session_state.manager_id is not None:
                    st.session_state.manager_id = None
                    manager_id = None
    elif q and len(q.strip()) >= 4:
        st.info("No matches found. Try a different search term or enter your manager ID directly (numbers only).")
    
    return st.session_state.manager_id


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
                st.session_state.selected_creator_team_id = None
            st.session_state.comparison_manager_id = manager_id


def render_similar_teams() -> Optional[Dict]:
    """
    Render Similar Teams section (pills) if comparison results exist.
    Returns selected creator team dict or None.
    """
    _init_comparison_state()
    if not st.session_state.comparison_results:
        return None
    with st.container(key="similar_teams_pills"):
        st.markdown('<p class="section-title">Similar Teams</p>', unsafe_allow_html=True)
        cols = st.columns(3)
        for idx, (creator_team, similarity) in enumerate(st.session_state.comparison_results):
            team_id = creator_team.get("team_id")
            manager_name = creator_team.get("manager_name", f"Team {team_id}")
            with cols[idx]:
                button_type = "primary" if st.session_state.selected_creator_team_id == team_id else "secondary"
                if st.button(manager_name, key=f"select_creator_{team_id}", use_container_width=True, type=button_type):
                    st.session_state.selected_creator_team_id = team_id
                    st.rerun()
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

