"""
Minimal Streamlit app: search manager → optional manual manager_id → fetch my-team → list picks.
Aligned with build_interface and fetch_data tickets.
"""

import base64
import os

import streamlit as st

from app.cache import (
    build_lookups,
    fetch_bootstrap_cached,
    fetch_entry_picks_cached,
    fetch_fixtures,
    get_current_event_id_cached,
)
from app.components import (
    process_manager_search,
    render_compare_section,
)
from app.rendering import creator_team_to_picks, render_pitch
from app.scheduler import is_scheduler_running, start_scheduler
from app.styles import get_app_styles

# Set favicon path - works for both local and Streamlit Cloud deployment
favicon_path = os.path.join("assets", "favicon.svg")
st.set_page_config(page_title="FPL Cheat", page_icon=favicon_path, layout="centered")


def _get_favicon_base64() -> str:
    """Convert favicon to base64 string for HTML embedding."""
    try:
        with open(favicon_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return ""

# Initialize scheduler once when the module loads
# The scheduler module uses a singleton pattern to ensure it only starts once
if not is_scheduler_running():
    start_scheduler()


def main():
    # Apply app styles
    st.markdown(get_app_styles(), unsafe_allow_html=True)
    
    # Title with logo - centered together using flexbox (no nested columns)
    favicon_b64 = _get_favicon_base64()
    st.markdown(f"""
        <div style="display: flex; align-items: center; justify-content: center; gap: 10px; margin-bottom: 0.5rem;">
            <img src="data:image/svg+xml;base64,{favicon_b64}" width="50" style="display: inline-block; vertical-align: middle;">
            <h1 style="margin: 0; display: inline-block; vertical-align: middle;">FPL Cheat</h1>
        </div>
        <p style="text-align: center; margin-top: 0; margin-bottom: 1rem; font-size: 0.9rem; font-weight: bold; color: rgba(255,255,255,0.8);">
            Are your mates cheating by copying FPL teams to get ahead? Catch them out using this team similarity tool
        </p>
    """, unsafe_allow_html=True)
    
    # Section 1: Setup (compact)
    st.markdown("### Select Your Team")
    
    # Get the query value from manager selection first
    manager_id = None
    q = None
    
    # Responsive search box - flex across full screen width
    st.markdown('<div class="search-container">', unsafe_allow_html=True)
    
    # Manager search input
    if "manager_id" not in st.session_state:
        st.session_state.manager_id = None
    
    manager_id = st.session_state.manager_id
    q = st.text_input("Search by Team name, Manager name, or Manager ID", placeholder="e.g. Gary Lineker or Winners 2025 or 9416474", label_visibility="visible")
    
    # Clear button (only show when manager_id exists)
    if manager_id:
        if st.button("Clear", key="clear_manager", use_container_width=False):
            st.session_state.manager_id = None
            st.rerun()
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    # Get default gameweek for data fetching (hidden from UI)
    default_gw = get_current_event_id_cached()
    event_id = default_gw
    
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
        selected_creator_team = render_compare_section(user_picks, element_lookup, int(event_id))
    
    # Section 3: Team Displays (side-by-side)
    if user_picks and element_lookup and team_lookup and fixtures:
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
