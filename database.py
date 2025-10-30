"""
Supabase-only helpers for searching FPL managers in production DB.
Aligned with build_interface and fetch_data tickets.
"""

from typing import List, Dict

import streamlit as st

try:
    from supabase import create_client
except ImportError as e:
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
