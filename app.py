"""
Minimal Streamlit app: search manager → fetch team → compare with creators.
Clean structure: header, then section cards (Select Your Team, Similar Teams, Team Comparison).
"""

import base64
import os
import time

import streamlit as st
from streamlit_searchbox import st_searchbox

from app.cache import (
    build_lookups,
    fetch_bootstrap_cached,
    fetch_entry_picks_cached,
    fetch_fixtures,
    get_current_event_id_cached,
)
from app.components import (
    manager_searchbox_options,
    render_similar_teams,
    run_compare_if_needed,
)
from app.rendering import creator_team_to_picks, pitch_as_html, render_pitch
from app.scheduler import is_scheduler_running, start_scheduler
from app.styles import get_app_styles

favicon_path = os.path.join("assets", "favicon.svg")
st.set_page_config(page_title="FPL Cheat", page_icon=favicon_path, layout="wide")


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
            <p class="tagline">Are your mates cheating by copying FPL teams to get ahead? 
            <br> Catch them out using this team similarity tool.</p>
        </div>
    """, unsafe_allow_html=True)

    event_id = get_current_event_id_cached()

    # --- Section 1: Select Your Team ---
    st.markdown("### Select Your Team")

    @st.fragment
    def select_team_section():
        """Isolated fragment so typing only reruns this block, not the whole page."""
        if "manager_id" not in st.session_state:
            st.session_state.manager_id = None

        def _on_manager_submit(manager_id_value):
            """After selecting a manager, set search bar to the selected label and clear options."""
            key = "manager_searchbox"
            if key not in st.session_state:
                return
            opts_py = st.session_state[key].get("options_py", [])
            opts_js = st.session_state[key].get("options_js", [])
            try:
                idx = opts_py.index(manager_id_value)
                label = opts_js[idx]["label"]
            except (ValueError, IndexError, KeyError):
                label = f"Manager ID {manager_id_value}"
            st.session_state[key]["search"] = label
            st.session_state[key]["options_js"] = []
            st.session_state[key]["options_py"] = []
            # Force component to remount so it shows the new default_searchterm (selected name)
            st.session_state[key]["key_react"] = f"{key}_react_{time.time()}"
            st.rerun()

        st.markdown(
            '<p class="search-section-label">Search by team name, manager name, or manager ID</p>',
            unsafe_allow_html=True,
        )
        with st.container(key="search_clear_row"):
            search_col, clear_col = st.columns([5, 1], vertical_alignment="top")
            with search_col:
                selected_value = st_searchbox(
                    manager_searchbox_options,
                    placeholder="e.g. Gary Lineker or 9416474",
                    key="manager_searchbox",
                    clear_on_submit=False,  # we set search term in submit_function instead
                    default_options=[],
                    default_searchterm=st.session_state.get("manager_searchbox", {}).get("search", ""),  # show selected name after submit
                    submit_function=_on_manager_submit,
                    rerun_scope="fragment",  # only this fragment reruns on keystroke, not whole app
                    style_overrides={
                        "searchbox": {
                            # Show empty-state message when dropdown opens (e.g. "No matches" until user types or when no matches)
                            "menuList": {"minHeight": 0, "maxHeight": "none"},
                        },
                    },
                )
                if selected_value is not None:
                    st.session_state.manager_id = int(selected_value)
            with clear_col:
                if st.button(
                    "Clear",
                    key="clear_manager",
                    use_container_width=True,
                    disabled=not st.session_state.manager_id,
                ):
                    st.session_state.manager_id = None
                    if "manager_searchbox" in st.session_state:
                        del st.session_state["manager_searchbox"]
                    st.rerun()

    select_team_section()

    manager_id = st.session_state.manager_id

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

    # --- Section 2: Similar Teams (only when results exist); Section 3: Team Comparison ---
    # When we have comparison results, wrap pills + comparison in a fragment so pill clicks
    # only rerun that block (no full page refresh).
    if user_picks and element_lookup and team_lookup and fixtures:
        has_comparison_results = bool(st.session_state.get("comparison_results"))

        if has_comparison_results:

            @st.fragment
            def similar_teams_and_comparison():
                selected_creator_team = render_similar_teams()
                team1_html = pitch_as_html(user_picks, element_lookup, team_lookup, title="Your Team", show_bench=True, small=True)
                if selected_creator_team:
                    creator_picks = creator_team_to_picks(selected_creator_team, element_lookup)
                    manager_name = selected_creator_team.get("manager_name", "Creator Team")
                    team2_html = pitch_as_html(creator_picks, element_lookup, team_lookup, title=manager_name, show_bench=True, small=True)
                else:
                    team2_html = '<p class="team-box-placeholder">👆 Select a creator team above to compare</p>'
                st.markdown(
                    f'<div class="section-card team-comparison-section">'
                    f'<div class="section-header-row">'
                    f'<h3 class="section-title" id="team-comparison">Team Comparison</h3>'
                    f'<span class="section-gw">Gameweek {event_id}</span>'
                    f'</div>'
                    f'<div class="team-comparison-row">'
                    f'<div class="team-box">{team1_html}</div>'
                    f'<div class="team-box">{team2_html}</div>'
                    f'</div></div>',
                    unsafe_allow_html=True,
                )

            similar_teams_and_comparison()
        else:
            # No similar teams yet; show comparison section with placeholder only
            team1_html = pitch_as_html(user_picks, element_lookup, team_lookup, title="Your Team", show_bench=True, small=True)
            team2_html = '<p class="team-box-placeholder">👆 Select a creator team above to compare</p>'
            st.markdown(
                f'<div class="section-card team-comparison-section">'
                f'<div class="section-header-row">'
                f'<h3 class="section-title" id="team-comparison">Team Comparison</h3>'
                f'<span class="section-gw">Gameweek {event_id}</span>'
                f'</div>'
                f'<div class="team-comparison-row">'
                f'<div class="team-box">{team1_html}</div>'
                f'<div class="team-box">{team2_html}</div>'
                f'</div></div>',
                unsafe_allow_html=True,
            )


if __name__ == "__main__":
    main()
