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
from dotenv import load_dotenv
from supabase import create_client, Client
import time

# Load environment variables
load_dotenv()

# Page config
st.set_page_config(
    page_title="FPL Cheat",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded"
)

# FPL API configuration
FPL_BASE_URL = "https://fantasy.premierleague.com/api"
FPL_BOOTSTRAP_URL = f"{FPL_BASE_URL}/bootstrap-static/"
FPL_TEAM_URL = f"{FPL_BASE_URL}/entry/{{team_id}}/event/{{gameweek}}/picks/"

# Initialize Supabase client
@st.cache_resource
def init_supabase() -> Optional[Client]:
    """Initialize Supabase client using environment variables."""
    try:
        url = os.getenv("SUPABASE_URL")
        key = os.getenv("SUPABASE_ANON_KEY")
        
        if not url or not key:
            st.error("Supabase credentials not found. Please check your environment variables.")
            return None
            
        return create_client(url, key)
    except Exception as e:
        st.error(f"Failed to initialize Supabase: {e}")
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
def save_creator_team(supabase: Client, team_name: str, squad_data: Dict) -> bool:
    """Save creator team data to Supabase."""
    try:
        result = supabase.table('creator_teams').insert({
            'team_name': team_name,
            'squad_data': squad_data,
            'created_at': 'now()'
        }).execute()
        return True
    except Exception as e:
        st.error(f"Failed to save creator team: {e}")
        return False

def get_creator_teams(supabase: Client) -> List[Dict]:
    """Fetch all creator teams from Supabase."""
    try:
        result = supabase.table('creator_teams').select('*').execute()
        return result.data if result.data else []
    except Exception as e:
        st.error(f"Failed to fetch creator teams: {e}")
        return []

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

def find_best_match(user_squad: List[int], creator_teams: List[Dict]) -> Tuple[Optional[Dict], float]:
    """Find the best matching creator team."""
    if not creator_teams or not user_squad:
        return None, 0.0
    
    best_match = None
    best_score = 0.0
    
    for team in creator_teams:
        squad_data = team.get('squad_data', {})
        picks = squad_data.get('picks', [])
        creator_squad = [pick.get('element') for pick in picks if pick.get('element')]
        
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
    
    best_match, similarity_score = find_best_match(user_squad, creator_teams)
    
    if best_match:
        st.success(f"🎯 Best Match: {best_match['team_name']}")
        st.metric("Similarity Score", f"{similarity_score:.2%}")
        
        # Show detailed comparison
        with st.expander("Detailed Comparison"):
            st.write(f"**Your team similarity with {best_match['team_name']}:**")
            
            # Create comparison table
            comparison_data = []
            for team in creator_teams:
                squad_data = team.get('squad_data', {})
                picks = squad_data.get('picks', [])
                creator_squad = [pick.get('element') for pick in picks if pick.get('element')]
                similarity = calculate_similarity(user_squad, creator_squad)
                
                comparison_data.append({
                    'Creator': team['team_name'],
                    'Similarity': f"{similarity:.2%}",
                    'Players in Common': len(set(user_squad).intersection(set(creator_squad)))
                })
            
            df = pd.DataFrame(comparison_data)
            df = df.sort_values('Similarity', ascending=False)
            st.dataframe(df, use_container_width=True)
    else:
        st.error("No matches found.")

def render_creator_management(supabase: Client, fpl_data: Dict):
    """Render creator team management section."""
    st.header("👥 Manage Creator Teams")
    
    with st.form("add_creator_team"):
        st.subheader("Add New Creator Team")
        creator_name = st.text_input("Creator Name", placeholder="e.g., FPL General")
        creator_team_name = st.text_input("FPL Team Name", placeholder="Enter their FPL team name")
        
        if st.form_submit_button("Add Creator Team"):
            if creator_name and creator_team_name:
                team_id = find_team_id(creator_team_name, fpl_data)
                if team_id:
                    squad_data = fetch_team_squad(team_id)
                    if squad_data:
                        if save_creator_team(supabase, creator_name, squad_data):
                            st.success(f"Added {creator_name} successfully!")
                            st.rerun()
                        else:
                            st.error("Failed to save creator team.")
                    else:
                        st.error("Failed to fetch squad data.")
                else:
                    st.error("Team not found. Please check the team name.")
            else:
                st.error("Please fill in all fields.")
    
    # Display existing creator teams
    st.subheader("Current Creator Teams")
    creator_teams = get_creator_teams(supabase)
    
    if creator_teams:
        for team in creator_teams:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"**{team['team_name']}**")
            with col2:
                if st.button("Remove", key=f"remove_{team['id']}"):
                    # Add removal logic here
                    st.info("Removal functionality to be implemented")
    else:
        st.info("No creator teams added yet.")

# Main app
def main():
    """Main application function."""
    st.title("⚽ FPL Cheat")
    st.markdown("Compare your Fantasy Premier League team with content creator teams!")
    
    # Initialize Supabase
    supabase = init_supabase()
    if not supabase:
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
                        creator_teams = get_creator_teams(supabase)
                        render_team_comparison(user_squad, creator_teams, fpl_data)
                    else:
                        st.error("Failed to fetch squad data.")
                else:
                    st.error(f"Team '{team_name}' not found. Please check the spelling.")
    
    elif page == "Manage Creators":
        render_creator_management(supabase, fpl_data)

if __name__ == "__main__":
    main()
