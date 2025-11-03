"""
Supabase-only helpers for searching FPL managers in production DB.
Aligned with build_interface and fetch_data tickets.
"""

from typing import List, Dict, Optional

import streamlit as st

try:
    from supabase import create_client
except ImportError:
    create_client = None  # Streamlit UI will surface a clear error


@st.cache_resource
def get_client():
    """Return a cached Supabase client using Streamlit secrets."""
    if create_client is None:
        raise ImportError("Supabase client not installed. Run: pip install supabase")
    if "supabase" not in st.secrets:
        raise RuntimeError("Supabase secrets missing. Add supabase.url and supabase.key to secrets.")
    url = st.secrets["supabase"].get("url")
    key = st.secrets["supabase"].get("key")
    if not url or not key:
        raise RuntimeError("Supabase url/key not configured in secrets.")
    return create_client(url, key)


def search_managers(query: str) -> List[Dict]:
    """Search `all_managers` by manager_name or team_name using case-sensitive prefix LIKE.
    Enforces a minimal query length to avoid timeouts and leverage btree indexes.
    """
    client = get_client()
    q = query.strip()
    if len(q) < 3:
        return []
    pattern = f"{q}%"  # prefix match to leverage existing btree indexes
    resp = (
        client
        .table("all_managers")
        .select("manager_id,manager_name,team_name")
        .or_(f"manager_name.like.{pattern},team_name.like.{pattern}")
        .limit(50)
        .execute()
    )
    return resp.data or []


def upsert_creator_team(team_data: Dict) -> bool:
    """Insert or update a creator team in the creator_teams table."""
    try:
        client = get_client()
        client.table("creator_teams").upsert(
            team_data,
            on_conflict="team_id"
        ).execute()
        return True
    except Exception as e:
        st.error(f"Failed to upsert creator team: {e}")
        return False


def get_creator_teams() -> List[Dict]:
    """Retrieve all creator teams from the database."""
    try:
        client = get_client()
        resp = client.table("creator_teams").select("*").execute()
        return resp.data or []
    except Exception as e:
        st.error(f"Failed to get creator teams: {e}")
        return []


def get_creator_team(team_id: int) -> Optional[Dict]:
    """Get a specific creator team by team_id."""
    try:
        client = get_client()
        resp = client.table("creator_teams").select("*").eq("team_id", team_id).execute()
        if resp.data:
            return resp.data[0]
        return None
    except Exception as e:
        st.error(f"Failed to get creator team: {e}")
        return None


def get_current_creator_gameweek() -> Optional[int]:
    """Get the current gameweek from creator_teams table (returns None if no teams exist)."""
    try:
        client = get_client()
        resp = client.table("creator_teams").select("current_gameweek").limit(1).execute()
        if resp.data and len(resp.data) > 0:
            return resp.data[0].get("current_gameweek")
        return None
    except Exception as e:
        if st:
            st.debug(f"Failed to get current creator gameweek: {e}")
        return None
