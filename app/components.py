"""
UI components for the FPL Cheat app.
"""

from typing import Dict, List, Optional

import streamlit as st

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


def render_compare_section(
    user_picks: List[Dict],
    element_lookup: Dict[int, Dict[str, str]],
    current_gameweek: int
) -> Optional[Dict]:
    """
    Render compare button and comparison results.
    
    Args:
        user_picks: List of pick dicts from user team
        element_lookup: Element lookup dict
        current_gameweek: Current gameweek number
    
    Returns:
        Selected creator team dict if one is selected, None otherwise
    """
    # Initialize session state
    if "comparison_results" not in st.session_state:
        st.session_state.comparison_results = None
    if "selected_creator_team_id" not in st.session_state:
        st.session_state.selected_creator_team_id = None
    
    # Compare button - centered
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        compare_button = st.button("Compare Teams", type="primary", use_container_width=True)
    
    if compare_button:
        with st.spinner("Comparing teams..."):
            # Get creator teams for current gameweek
            creator_teams = get_creator_teams()
            # Filter by current gameweek
            creator_teams = [t for t in creator_teams if t.get("current_gameweek") == current_gameweek]
            
            if not creator_teams:
                st.warning("No creator teams available for current gameweek. Please update creator teams first.")
                st.session_state.comparison_results = None
            else:
                # Find top similar teams
                top_matches = find_top_similar_teams(user_picks, creator_teams, element_lookup, top_n=3)
                st.session_state.comparison_results = top_matches
                st.session_state.selected_creator_team_id = None  # Reset selection
    
    # Display comparison results
    if st.session_state.comparison_results:
        st.markdown("**Similar Teams:**")
        
        # Create compact buttons for each similar team
        cols = st.columns(3)
        for idx, (creator_team, similarity) in enumerate(st.session_state.comparison_results):
            team_id = creator_team.get("team_id")
            manager_name = creator_team.get("manager_name", f"Team {team_id}")
            
            with cols[idx]:
                # Highlight selected team
                button_type = "primary" if st.session_state.selected_creator_team_id == team_id else "secondary"
                
                # Use metric-style display for similarity
                if st.button(f"{manager_name}", key=f"select_creator_{team_id}", use_container_width=True, type=button_type):
                    st.session_state.selected_creator_team_id = team_id
                
                # Show similarity below button
                st.caption(f"{similarity}% similar")
        
        # Get selected creator team
        selected_team_id = st.session_state.selected_creator_team_id
        if selected_team_id:
            # Find the creator team in results
            for creator_team, _ in st.session_state.comparison_results:
                if creator_team.get("team_id") == selected_team_id:
                    return creator_team
    
    return None

