"""
UI components for the FPL Cheat app.
"""

import streamlit as st

from app.database import search_managers
from app.update_creator_teams import update_all_creator_teams


def render_creator_teams_update():
    """Render the creator teams update section."""
    st.divider()
    st.subheader("Creator Teams")
    st.caption("Update content creator teams for current gameweek")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        update_button = st.button("Update Creator Teams", type="primary", use_container_width=True)
    
    if update_button:
        # Quick check if already up to date
        quick_check = update_all_creator_teams(progress_callback=None)
        
        if quick_check.get("already_up_to_date", False):
            st.info("Teams are already up to date")
        else:
            # Update teams with progress display
            status_container = st.status("Updating creator teams...", expanded=True)
            progress_text = status_container.empty()
            
            def progress_callback(message: str):
                progress_text.text(message)
            
            # Re-run update with progress display
            results = update_all_creator_teams(progress_callback=progress_callback)
            
            status_container.update(
                label=f"Update complete: {results['success']}/{results['total']} successful",
                state="complete" if results['failed'] == 0 else "error"
            )
            
            if results['success'] > 0:
                st.success(f"✅ Successfully updated {results['success']} team(s)")
            if results['failed'] > 0:
                st.error(f"❌ Failed to update {results['failed']} team(s)")


def render_manager_selection() -> int | None:
    """Render manager selection UI and return selected manager_id."""
    if "manager_id" not in st.session_state:
        st.session_state.manager_id = None
    
    q = st.text_input("Team or Manager name", placeholder="e.g., John or United")
    manager_id = st.session_state.manager_id

    # Fetch matches when there's a query
    matches = []
    if q:
        try:
            matches = search_managers(q)
        except Exception as e:
            st.error(f"Database error: {e}")
            matches = []

    # Handle matches
    if matches:
        if len(matches) == 1:
            # Auto-select if only one match
            if manager_id != matches[0]["manager_id"]:
                manager_id = matches[0]["manager_id"]
                st.session_state.manager_id = manager_id
        else:
            # Show dropdown for multiple matches (always visible, collapsed when selected)
            # Add placeholder option for "no selection"
            placeholder = "--- Select a manager ---"
            labels = [placeholder] + [
                f"{m['manager_name']} — {m['team_name']} (id {m['manager_id']})"
                for m in matches
            ]
            
            # Find current selection index (0 = placeholder, 1+ = actual managers)
            current_index = 0  # Default to placeholder (no selection)
            if manager_id:
                for idx, m in enumerate(matches):
                    if m['manager_id'] == manager_id:
                        current_index = idx + 1  # +1 because of placeholder
                        break
                # If selected manager not in current matches, clear selection
                if current_index == 0 and manager_id:
                    st.session_state.manager_id = None
                    manager_id = None
                    current_index = 0
            
            # Use a stable key - Streamlit will automatically manage the selectbox value
            selectbox_key = "manager_selectbox"
            
            # Initialize selectbox value based on current manager_id
            if selectbox_key not in st.session_state:
                # First time: set to placeholder or selected manager
                if manager_id and current_index > 0:
                    st.session_state[selectbox_key] = labels[current_index]
                else:
                    st.session_state[selectbox_key] = placeholder
            else:
                # If manager_id exists but selectbox doesn't match, update selectbox
                if manager_id and current_index > 0:
                    expected_label = labels[current_index]
                    if st.session_state[selectbox_key] != expected_label:
                        st.session_state[selectbox_key] = expected_label
                elif not manager_id and st.session_state[selectbox_key] != placeholder:
                    # If no manager selected but selectbox isn't placeholder, reset it
                    # But only if the current value isn't in the labels (matches changed)
                    if st.session_state[selectbox_key] not in labels:
                        st.session_state[selectbox_key] = placeholder
            
            # Get the index of the current selectbox value
            current_value = st.session_state.get(selectbox_key, placeholder)
            if current_value in labels:
                display_index = labels.index(current_value)
            else:
                display_index = current_index
            
            choice = st.selectbox(
                "Select your manager:", 
                labels, 
                index=display_index,
                key=selectbox_key
            )
            
            # Process selection - Streamlit automatically reruns when selectbox changes
            if choice and choice != placeholder:
                try:
                    selected_id = int(choice.split("id ")[-1].strip(")"))
                    # Update manager_id if selection changed
                    if st.session_state.manager_id != selected_id:
                        st.session_state.manager_id = selected_id
                except (ValueError, IndexError):
                    # If parsing fails, keep current selection
                    pass
            elif choice == placeholder:
                # User selected placeholder, clear selection
                if st.session_state.manager_id is not None:
                    st.session_state.manager_id = None
    elif q:
        st.info("No matches found. You can enter your manager_id manually below.")
    
    # Get manager_id from session state after potential updates
    manager_id = st.session_state.manager_id

    # Manual manager_id
    if manager_id is None:
        manual = st.checkbox("Enter manager_id manually")
        if manual or q:
            val = st.text_input("manager_id", placeholder="e.g., 123456")
            if val.isdigit():
                manager_id = int(val)
                st.session_state.manager_id = manager_id

    # Reset button to clear selection
    if manager_id:
        col1, col2 = st.columns([1, 10])
        with col1:
            if st.button("Clear selection"):
                st.session_state.manager_id = None
                st.rerun()
    
    return st.session_state.manager_id

