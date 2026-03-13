"""
Minimal Streamlit app: search manager → fetch team → compare with creators.
Clean structure: header, then section cards (Select Your Team, Similar Teams, Team Comparison).
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
    render_similar_teams,
    run_compare_if_needed,
)
from app.rendering import creator_team_to_picks, pitch_as_html, render_pitch
from app.scheduler import is_scheduler_running, start_scheduler
from app.styles import get_app_styles

favicon_path = os.path.join("assets", "favicon.svg")
st.set_page_config(page_title="FPL Cheat", page_icon=favicon_path, layout="centered")


def _get_favicon_base64() -> str:
    try:
        with open(favicon_path, "rb") as f:
            return base64.b64encode(f.read()).decode("ascii")
    except Exception:
        return ""

if not is_scheduler_running():
    start_scheduler()


def main():
    st.markdown(get_app_styles(), unsafe_allow_html=True)

    favicon_b64 = _get_favicon_base64()
    st.markdown(f"""
        <div class="app-header">
            <div class="logo-title">
                <img src="data:image/svg+xml;base64,{favicon_b64}" width="52" height="52" alt="FPL Cheat" />
                <h1>FPL Cheat</h1>
            </div>
            <p class="tagline">Are your mates cheating by copying FPL teams to get ahead? Catch them out using this team similarity tool.</p>
        </div>
    """, unsafe_allow_html=True)

    event_id = get_current_event_id_cached()

    # --- Section 1: Select Your Team ---
    st.markdown("### Select Your Team")

    if "manager_id" not in st.session_state:
        st.session_state.manager_id = None
    manager_id = st.session_state.manager_id

    search_col, clear_col = st.columns([5, 1], vertical_alignment="bottom")
    with search_col:
        q = st.text_input(
            "Search by Team name, Manager name, or Manager ID",
            placeholder="e.g. Gary Lineker or Winners 2025 or 9416474",
            label_visibility="visible",
            key="manager_search_input",
        )
    with clear_col:
        if st.button("Clear", key="clear_manager", use_container_width=True, disabled=not manager_id):
            st.session_state.manager_id = None
            st.rerun()

    manager_id = process_manager_search(q, manager_id)

    # Load team data when manager is selected
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

    # Run comparison automatically when a manager is selected and team is loaded
    if user_picks and element_lookup:
        run_compare_if_needed(user_picks, element_lookup, int(event_id), manager_id)

    # --- Section 2: Similar Teams (only when results exist) ---
    selected_creator_team = None
    if user_picks and element_lookup and st.session_state.get("comparison_results"):
        selected_creator_team = render_similar_teams()

    # --- Section 3: Team Comparison (each team in its own box, no line; smaller players) ---
    if user_picks and element_lookup and team_lookup and fixtures:
        team1_html = pitch_as_html(user_picks, element_lookup, team_lookup, title="Your Team", show_bench=True, small=True)
        if selected_creator_team:
            creator_picks = creator_team_to_picks(selected_creator_team, element_lookup)
            manager_name = selected_creator_team.get("manager_name", "Creator Team")
            team2_html = pitch_as_html(creator_picks, element_lookup, team_lookup, title=manager_name, show_bench=True, small=True)
        else:
            team2_html = '<p class="team-box-placeholder">👆 Select a creator team above to compare</p>'
        st.markdown(
            f'<div class="section-card team-comparison-section">'
            f'<h3 class="section-title">Team Comparison</h3>'
            f'<div class="team-comparison-row">'
            f'<div class="team-box">{team1_html}</div>'
            f'<div class="team-box">{team2_html}</div>'
            f'</div></div>',
            unsafe_allow_html=True,
        )


if __name__ == "__main__":
    main()
