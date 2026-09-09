"""
Minimal Streamlit app: search manager → fetch team → compare with creators.
Clean structure: header, then section cards (Select Your Team, Similar Teams, Team Comparison).
"""

import time

import streamlit as st
from streamlit_searchbox import st_searchbox

from app.assets import get_favicon_data_uri
from app.cache import (
    build_lookups,
    fetch_bootstrap_cached,
    fetch_entry_picks_cached,
    get_current_event_id_cached,
)
from app.components import (
    manager_searchbox_options,
    render_similar_teams,
    run_compare_if_needed,
)
from app.rendering import PLACEHOLDER, creator_team_to_picks, pitch_as_html
from app.scheduler import is_scheduler_running, start_scheduler
from app.styles import get_app_styles

# Streamlit passes a data: URI straight through; raw SVG bytes would fail.
_FAVICON_DATA_URI = get_favicon_data_uri()
st.set_page_config(
    page_title="FPL Cheat", page_icon=_FAVICON_DATA_URI or "⚽", layout="wide"
)

if not is_scheduler_running():
    start_scheduler()


def _element_ids(picks: list[dict]) -> set[int]:
    return {int(p["element"]) for p in picks if p.get("element") is not None}


def render_comparison(
    user_picks: list[dict],
    element_lookup: dict[int, dict[str, str]],
    team_lookup: dict[int, dict[str, str]],
    event_id: int,
    creator_team: dict | None = None,
) -> None:
    """Render the Team Comparison card: the user's pitch beside the selected creator's, or a placeholder."""
    common_player_ids = None
    creator_html = PLACEHOLDER
    if creator_team:
        creator_picks = creator_team_to_picks(creator_team, element_lookup)
        common_player_ids = _element_ids(user_picks) & _element_ids(creator_picks)
        creator_html = pitch_as_html(
            creator_picks,
            element_lookup,
            team_lookup,
            title=creator_team.get("manager_name", "Creator Team"),
            common_player_ids=common_player_ids,
        )
    user_html = pitch_as_html(
        user_picks,
        element_lookup,
        team_lookup,
        title="Your Team",
        common_player_ids=common_player_ids,
    )
    st.markdown(
        f'<div class="section-card team-comparison-section">'
        f'<div class="section-header-row">'
        f'<h3 class="section-title" id="team-comparison">Team Comparison</h3>'
        f'<span class="section-gw">Gameweek {event_id}</span>'
        f"</div>"
        f'<div class="team-comparison-row">'
        f'<div class="team-box">{user_html}</div>'
        f'<div class="team-box">{creator_html}</div>'
        f"</div></div>",
        unsafe_allow_html=True,
    )


@st.fragment
def select_team_section():
    """Isolated fragment so typing only reruns this block, not the whole page."""
    st.session_state.setdefault("manager_id", None)

    def _on_manager_submit(manager_id_value):
        """After selecting a manager, set search bar to the selected label and clear options."""
        key = "manager_searchbox"
        if key not in st.session_state:
            return
        opts_py = st.session_state[key].get("options_py", [])
        opts_js = st.session_state[key].get("options_js", [])
        try:
            label = opts_js[opts_py.index(manager_id_value)]["label"]
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
                default_searchterm=st.session_state.get("manager_searchbox", {}).get(
                    "search", ""
                ),  # show selected name after submit
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
                st.session_state.pop("manager_searchbox", None)
                st.rerun()


def main():
    st.markdown(get_app_styles(), unsafe_allow_html=True)

    # An empty src renders a broken-image icon, so omit the tag entirely.
    logo_img = (
        f'<img src="{_FAVICON_DATA_URI}" width="52" height="52" alt="FPL Cheat" />'
        if _FAVICON_DATA_URI
        else ""
    )
    st.markdown(
        f"""
        <div class="app-header">
            <div class="logo-title">
                {logo_img}
                <h1>FPL Cheat</h1>
            </div>
            <p class="tagline">Are your mates cheating by copying FPL teams to get ahead?
            <br> Catch them out using this team similarity tool.</p>
        </div>
    """,
        unsafe_allow_html=True,
    )

    event_id = int(get_current_event_id_cached())

    # --- Section 1: Select Your Team ---
    st.markdown("### Select Your Team")
    select_team_section()
    manager_id = st.session_state.manager_id

    # Load team data when a manager is selected
    user_picks, element_lookup, team_lookup = None, None, None
    if manager_id:
        with st.spinner("Loading team..."):
            data = fetch_entry_picks_cached(manager_id, event_id)
        user_picks = (data or {}).get("picks") or None
        if data and not user_picks:
            st.warning("No picks found.")
        if user_picks:
            bootstrap = fetch_bootstrap_cached()
            if bootstrap:
                element_lookup, team_lookup = build_lookups(bootstrap)

    if not (user_picks and element_lookup and team_lookup):
        return

    # Comparison runs automatically once a manager is selected; no button.
    run_compare_if_needed(user_picks, element_lookup, manager_id)

    # --- Section 2: Similar Teams (only when results exist); Section 3: Team Comparison ---
    # With results, pills + comparison share a fragment so pill clicks only rerun that
    # block rather than refreshing the whole page.
    if st.session_state.get("comparison_results"):

        @st.fragment
        def similar_teams_and_comparison():
            render_comparison(
                user_picks,
                element_lookup,
                team_lookup,
                event_id,
                render_similar_teams(),
            )

        similar_teams_and_comparison()
    else:
        render_comparison(user_picks, element_lookup, team_lookup, event_id)


if __name__ == "__main__":
    main()
