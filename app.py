"""
Minimal Streamlit app: search manager → optional manual manager_id → fetch my-team → list picks.
Aligned with build_interface and fetch_data tickets.
"""

import os
import streamlit as st

from app.cache import (
    build_lookups,
    fetch_bootstrap_cached,
    fetch_entry_picks_cached,
    fetch_fixtures,
    get_current_event_id_cached,
)
from app.components import render_creator_teams_update, render_compare_section, process_manager_search
from app.rendering import render_pitch, creator_team_to_picks
from app.styles import get_app_styles

# Set favicon path - works for both local and Streamlit Cloud deployment
favicon_path = os.path.join("assets", "favicon.svg")
st.set_page_config(page_title="FPL Cheat", page_icon=favicon_path, layout="centered")


def main():
    st.title("FPL Cheat")
    
    # Apply app styles
    st.markdown(get_app_styles(), unsafe_allow_html=True)
    
    # Section 1: Setup (compact)
    with st.container():
        # Manager selection, gameweek, and creator teams update - all inline
        st.markdown("### Select Your Team")
        
        # Get the query value from manager selection first
        manager_id = None
        q = None
        
        # Create aligned columns - all inputs at same level
        col1, col2, col3, col4 = st.columns([3.5, 1, 1, 1.5])
        
        with col1:
            # Manager search input - no nested columns
            if "manager_id" not in st.session_state:
                st.session_state.manager_id = None
            
            manager_id = st.session_state.manager_id
            q = st.text_input("Team or Manager name / Manager ID", placeholder="e.g., John, United, or enter Manager ID (numbers)", label_visibility="visible")
        
        with col2:
            # Clear button aligned with input
            st.markdown("<br>", unsafe_allow_html=True)  # Spacer to align with label
            if manager_id:
                if st.button("Clear", key="clear_manager", use_container_width=True):
                    st.session_state.manager_id = None
                    st.rerun()
            else:
                # Empty space to maintain alignment
                st.write("")
        
        with col3:
            # Gameweek input - label above for consistency
            default_gw = get_current_event_id_cached()
            st.markdown('<p style="margin-bottom: 0.25rem; font-weight: 600;">Gameweek</p>', unsafe_allow_html=True)
            event_id = st.number_input("GW", min_value=1, max_value=38, value=default_gw, step=1, label_visibility="collapsed")
        
        with col4:
            # Update Creator Teams button - label above for consistency
            st.markdown('<p style="margin-bottom: 0.25rem; font-weight: 600;">Update Teams</p>', unsafe_allow_html=True)
            render_creator_teams_update()
        
        # Process manager selection logic
        manager_id = process_manager_search(q, manager_id)
        
        # Fetch user team data
        user_picks = None
        element_lookup = None
        team_lookup = None
        fixtures = None
        
        if manager_id:
            with st.spinner("Loading team..."):
                data = fetch_entry_picks_cached(manager_id, int(event_id))
            if data:
                user_picks = data.get("picks") or []
                if not user_picks:
                    st.warning("No picks found.")
                else:
                    bootstrap = fetch_bootstrap_cached()
                    if bootstrap:
                        element_lookup, team_lookup = build_lookups(bootstrap)
                        fixtures = fetch_fixtures(int(event_id))
    
    # Section 2: Comparison (only if team selected)
    selected_creator_team = None
    if user_picks and element_lookup:
        st.markdown("---")
        st.markdown("### Compare Teams")
        selected_creator_team = render_compare_section(user_picks, element_lookup, int(event_id))
    
    # Section 3: Team Displays (side-by-side)
    if user_picks and element_lookup and team_lookup and fixtures:
        st.markdown("---")
        st.markdown("### Team Comparison")
        
        # Two columns for team displays with divider
        col1, col_divider, col2 = st.columns([1, 0.05, 1])
        
        with col1:
            render_pitch(
                user_picks,
                element_lookup,
                team_lookup,
                fixtures,
                show_bench=True,
                title="Your Team"
            )
        
        with col_divider:
            # Vertical divider line
            st.markdown(
                '<div style="border-left: 2px solid rgba(255,255,255,0.4); height: 100%; min-height: 400px;"></div>',
                unsafe_allow_html=True
            )
        
        with col2:
            if selected_creator_team:
                # Convert creator team to picks format
                creator_picks = creator_team_to_picks(selected_creator_team, element_lookup)
                manager_name = selected_creator_team.get("manager_name", "Creator Team")
                render_pitch(
                    creator_picks,
                    element_lookup,
                    team_lookup,
                    fixtures,
                    show_bench=True,
                    title=manager_name
                )
            else:
                st.info("👆 Select a creator team above to compare")


if __name__ == "__main__":
    main()
