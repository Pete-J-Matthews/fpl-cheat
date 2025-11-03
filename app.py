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
from app.components import render_creator_teams_update, render_manager_selection
from app.rendering import render_picks_table, render_pitch
from app.styles import get_app_styles

# Set favicon path - works for both local and Streamlit Cloud deployment
favicon_path = os.path.join("assets", "favicon.svg")
st.set_page_config(page_title="FPL Cheat", page_icon=favicon_path, layout="centered")


def main():
    st.title("FPL Cheat")
    st.caption("Find your manager and view your current picks")
    
    # Creator teams update section
    render_creator_teams_update()
    
    # Apply app styles
    st.divider()
    st.markdown(get_app_styles(), unsafe_allow_html=True)

    # Manager selection
    manager_id = render_manager_selection()
    
    # Fetch and render picks
    if manager_id:
        default_gw = get_current_event_id_cached()
        event_id = st.number_input("Gameweek", min_value=1, max_value=38, value=default_gw, step=1)
        with st.spinner("Fetching your team picks..."):
            data = fetch_entry_picks_cached(manager_id, int(event_id))
        if not data:
            return
        picks = data.get("picks") or []
        if not picks:
            st.warning("No picks found.")
            return
        bootstrap = fetch_bootstrap_cached()
        if not bootstrap:
            return
        element_lookup, team_lookup = build_lookups(bootstrap)
        fixtures = fetch_fixtures(int(event_id))

        st.subheader("Your Team Picks")
        show_pitch = st.toggle("Pitch view", value=True)
        if show_pitch:
            render_pitch(picks, element_lookup, team_lookup, fixtures, show_bench=True)
        else:
            render_picks_table(picks, element_lookup)


if __name__ == "__main__":
    main()
