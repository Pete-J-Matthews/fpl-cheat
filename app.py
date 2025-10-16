"""
FPL Cheat - Fantasy Premier League Team Comparison App
Main Streamlit application for comparing user teams with content creator teams.
"""

import streamlit as st
import requests
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
import os
import time
from database import get_database, DatabaseInterface

# Page config
st.set_page_config(
    page_title="FPL Cheat",
    page_icon="favicon.png",
    layout="wide",
    initial_sidebar_state="expanded"
)

# FPL API configuration
FPL_BASE_URL = "https://fantasy.premierleague.com/api"
FPL_BOOTSTRAP_URL = f"{FPL_BASE_URL}/bootstrap-static/"
FPL_TEAM_URL = f"{FPL_BASE_URL}/entry/{{team_id}}/event/{{gameweek}}/picks/"

# Initialize database client
@st.cache_resource
def init_database() -> Optional[DatabaseInterface]:
    """Initialize database client (SQLite for local, Supabase for production)."""
    try:
        db = get_database()
        
        # Show which database we're using
        db_type = "SQLite (Local)" if isinstance(db, __import__('database').SQLiteDatabase) else "Supabase (Production)"
        st.sidebar.info(f"🗄️ Using: {db_type}")
        
        return db
    except Exception as e:
        st.error(f"Failed to initialize database: {e}")
        return None

# FPL API functions
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_fpl_data() -> Optional[Dict]:
    """Fetch FPL bootstrap data (players, teams, etc.)."""
    try:
        response = requests.get(FPL_BOOTSTRAP_URL, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch FPL data: {e}")
        return None

def find_team_id(team_name: str, fpl_data: Dict) -> Optional[int]:
    """Find team ID by team name."""
    if not fpl_data or 'elements' not in fpl_data:
        return None
    
    for player in fpl_data['elements']:
        if player.get('web_name', '').lower() == team_name.lower():
            return player.get('id')
    return None

@st.cache_data(ttl=60)  # Cache for 1 minute
def fetch_team_squad(team_id: int, gameweek: int = 1) -> Optional[Dict]:
    """Fetch team squad for specific gameweek."""
    try:
        url = FPL_TEAM_URL.format(team_id=team_id, gameweek=gameweek)
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Failed to fetch team squad: {e}")
        return None

# Database functions
def save_creator_team(db: DatabaseInterface, manager_name: str, team_name: str) -> bool:
    """Save creator team data to database."""
    return db.save_creator_team(manager_name, team_name)

def get_creator_teams(db: DatabaseInterface) -> List[Dict]:
    """Fetch all creator teams from database."""
    return db.get_creator_teams()

def delete_creator_team(db: DatabaseInterface, manager_id: int) -> bool:
    """Delete a creator team by ID."""
    return db.delete_creator_team(manager_id)

# Similarity calculation
def calculate_similarity(squad1: List[int], squad2: List[int]) -> float:
    """Calculate similarity between two squads based on player overlap."""
    if not squad1 or not squad2:
        return 0.0
    
    set1 = set(squad1)
    set2 = set(squad2)
    
    intersection = len(set1.intersection(set2))
    union = len(set1.union(set2))
    
    return intersection / union if union > 0 else 0.0

def find_creator_team_squad(team_name: str, fpl_data: Dict) -> Optional[List[int]]:
    """Find and fetch squad data for a creator team by team name."""
    team_id = find_team_id(team_name, fpl_data)
    if not team_id:
        return None
    
    squad_data = fetch_team_squad(team_id)
    if not squad_data:
        return None
    
    picks = squad_data.get('picks', [])
    return [pick.get('element') for pick in picks if pick.get('element')]

def find_best_match(user_squad: List[int], creator_teams: List[Dict], fpl_data: Dict) -> Tuple[Optional[Dict], float]:
    """Find the best matching creator team."""
    if not creator_teams or not user_squad:
        return None, 0.0
    
    best_match = None
    best_score = 0.0
    
    for team in creator_teams:
        team_name = team.get('team_name')
        creator_squad = find_creator_team_squad(team_name, fpl_data)
        
        if creator_squad:
            similarity = calculate_similarity(user_squad, creator_squad)
            
            if similarity > best_score:
                best_score = similarity
                best_match = team
    
    return best_match, best_score

# UI Components
def render_team_input():
    """Render team name input section."""
    st.header("🔍 Find Your Team")
    st.write("Enter your FPL team name to compare with content creator teams.")
    
    team_name = st.text_input(
        "Team Name",
        placeholder="Enter your FPL team name...",
        help="This should match exactly how it appears in FPL"
    )
    
    return team_name

def render_team_comparison(user_squad: List[int], creator_teams: List[Dict], fpl_data: Dict):
    """Render team comparison results."""
    if not user_squad or not creator_teams:
        st.warning("No data available for comparison.")
        return
    
    best_match, similarity_score = find_best_match(user_squad, creator_teams, fpl_data)
    
    if best_match:
        st.success(f"🎯 Best Match: {best_match['manager_name']} ({best_match['team_name']})")
        st.metric("Similarity Score", f"{similarity_score:.2%}")
        
        # Show detailed comparison
        with st.expander("Detailed Comparison"):
            st.write(f"**Your team similarity with {best_match['manager_name']}:**")
            
            # Create comparison table
            comparison_data = []
            for team in creator_teams:
                team_name = team.get('team_name')
                creator_squad = find_creator_team_squad(team_name, fpl_data)
                
                if creator_squad:
                    similarity = calculate_similarity(user_squad, creator_squad)
                    
                    comparison_data.append({
                        'Creator': team['manager_name'],
                        'FPL Team': team['team_name'],
                        'Similarity': f"{similarity:.2%}",
                        'Players in Common': len(set(user_squad).intersection(set(creator_squad)))
                    })
            
            if comparison_data:
                df = pd.DataFrame(comparison_data)
                df = df.sort_values('Similarity', ascending=False)
                st.dataframe(df, use_container_width=True)
            else:
                st.warning("Could not fetch squad data for any creator teams.")
    else:
        st.error("No matches found.")

def render_creator_management(db: DatabaseInterface, fpl_data: Dict):
    """Render creator team management section."""
    st.header("👥 Manage Creator Teams")
    
    with st.form("add_creator_team"):
        st.subheader("Add New Creator Team")
        manager_name = st.text_input("Creator Name", placeholder="e.g., FPL General")
        team_name = st.text_input("FPL Team Name", placeholder="Enter their FPL team name")
        
        if st.form_submit_button("Add Creator Team"):
            if manager_name and team_name:
                # Verify the team exists in FPL
                team_id = find_team_id(team_name, fpl_data)
                if team_id:
                    if save_creator_team(db, manager_name, team_name):
                        st.success(f"Added {manager_name} successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to save creator team.")
                else:
                    st.error("Team not found. Please check the team name.")
            else:
                st.error("Please fill in all fields.")
    
    # Display existing creator teams
    st.subheader("Current Creator Teams")
    creator_teams = get_creator_teams(db)
    
    if creator_teams:
        for team in creator_teams:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{team['manager_name']}** - {team['team_name']}")
            with col2:
                if st.button("Remove", key=f"remove_{team['manager_id']}"):
                    if delete_creator_team(db, team['manager_id']):
                        st.success(f"Removed {team['manager_name']} successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to remove creator team.")
    else:
        st.info("No creator teams added yet.")

# Main app
def main():
    """Main application function."""
    # Header with logo and title
    col1, col2 = st.columns([1, 4])
    with col1:
        st.image("favicon.png", width=80)
    with col2:
        st.title("FPL Cheat")
    
    st.markdown("Compare your Fantasy Premier League team with content creator teams!")
    
    # Initialize database
    db = init_database()
    if not db:
        st.stop()
    
    # Fetch FPL data
    with st.spinner("Loading FPL data..."):
        fpl_data = fetch_fpl_data()
    
    if not fpl_data:
        st.error("Failed to load FPL data. Please try again later.")
        st.stop()
    
    # Sidebar for navigation
    page = st.sidebar.selectbox(
        "Navigation",
        ["Team Comparison", "Manage Creators"]
    )
    
    if page == "Team Comparison":
        # Team input
        team_name = render_team_input()
        
        if team_name:
            with st.spinner(f"Searching for {team_name}..."):
                team_id = find_team_id(team_name, fpl_data)
                
                if team_id:
                    st.success(f"Found team: {team_name} (ID: {team_id})")
                    
                    # Fetch squad
                    squad_data = fetch_team_squad(team_id)
                    if squad_data:
                        picks = squad_data.get('picks', [])
                        user_squad = [pick.get('element') for pick in picks if pick.get('element')]
                        
                        # Get creator teams and compare
                        creator_teams = get_creator_teams(db)
                        render_team_comparison(user_squad, creator_teams, fpl_data)
                    else:
                        st.error("Failed to fetch squad data.")
                else:
                    st.error(f"Team '{team_name}' not found. Please check the spelling.")
    
    elif page == "Manage Creators":
        render_creator_management(db, fpl_data)

if __name__ == "__main__":
    main()
