"""
PostgreSQL database helpers for searching FPL managers in production DB.
Uses Railway PostgreSQL database via DATABASE_URL from Streamlit secrets.
"""

from contextlib import contextmanager
from typing import Any, Callable, Dict, List, Optional, TypeVar

import streamlit as st

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    psycopg2 = None
    RealDictCursor = None

T = TypeVar('T')


@st.cache_resource
def get_database_url():
    """Return cached DATABASE_URL from Streamlit secrets."""
    database_url = st.secrets.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "Database credentials missing. Set DATABASE_URL in .streamlit/secrets.toml"
        )
    return database_url


@contextmanager
def get_connection():
    """Context manager for PostgreSQL connections."""
    if psycopg2 is None:
        raise ImportError("psycopg2 not installed. Run: pip install psycopg2-binary")
    
    conn = psycopg2.connect(get_database_url())
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def _execute_query(
    query: str,
    params: tuple = (),
    use_dict_cursor: bool = False,
    fetch_one: bool = False,
    error_handler: Optional[Callable[[Exception], T]] = None,
) -> Any:
    """Execute a database query and return results.
    
    Args:
        query: SQL query string
        params: Query parameters
        use_dict_cursor: If True, use RealDictCursor for dict results
        fetch_one: If True, fetch one row; otherwise fetch all
        error_handler: Optional function to handle errors, returns default value
    
    Returns:
        Query results (list of dicts, single dict, single value, True/False for write ops, or None)
    """
    try:
        with get_connection() as conn:
            cursor_factory = RealDictCursor if use_dict_cursor else None
            cursor = conn.cursor(cursor_factory=cursor_factory)
            cursor.execute(query, params)
            
            # Check if this is a write operation (INSERT, UPDATE, DELETE)
            query_upper = query.strip().upper()
            is_write_op = any(query_upper.startswith(op) for op in ['INSERT', 'UPDATE', 'DELETE'])
            
            if is_write_op:
                # For write operations, return True if rows were affected, False otherwise
                return cursor.rowcount > 0
            
            # For SELECT queries, fetch results as before
            if fetch_one:
                result = cursor.fetchone()
                if use_dict_cursor and result:
                    return dict(result)
                return result[0] if result and not use_dict_cursor else result
            else:
                results = cursor.fetchall()
                if use_dict_cursor:
                    return [dict(row) for row in results]
                return results
    except Exception as e:
        if error_handler:
            return error_handler(e)
        raise


def _handle_timeout_error(e: Exception) -> None:
    """Handle database timeout errors with user-friendly message."""
    error_msg = str(e)
    if "timeout" in error_msg.lower() or "57014" in error_msg:
        raise Exception(
            "Database query timed out. The database may be under heavy load. "
            "Please try:\n"
            "1. Using a longer/more specific search term (at least 4 characters)\n"
            "2. Entering your manager ID directly (numbers only)\n"
            "3. Trying again in a few moments"
        )
    raise


def _handle_st_error(operation: str, default_return: Any = None):
    """Return error handler that logs to st.error and returns default value."""
    def handler(e: Exception) -> Any:
        st.error(f"Failed to {operation}: {e}")
        return default_return
    return handler


def _handle_st_debug(operation: str, default_return: Any = None):
    """Return error handler that logs to st.debug and returns default value."""
    def handler(e: Exception) -> Any:
        st.debug(f"Failed to {operation}: {e}")
        return default_return
    return handler


def search_managers(query: str) -> List[Dict]:
    """Search `all_managers` by manager_name or team_name using case-insensitive prefix ILIKE."""
    q = query.strip()
    if len(q) < 4:
        return []
    
    pattern = f"{q}%"
    return _execute_query(
        """
        SELECT DISTINCT manager_id, manager_name, team_name
        FROM all_managers
        WHERE manager_name ILIKE %s OR team_name ILIKE %s
        LIMIT 50
        """,
        params=(pattern, pattern),
        use_dict_cursor=True,
        error_handler=_handle_timeout_error,
    )


def upsert_creator_team(team_data: Dict) -> bool:
    """Insert or update a creator team in the creator_teams table."""
    columns = list(team_data.keys())
    values = [team_data[col] for col in columns]
    placeholders = ', '.join(['%s'] * len(values))
    column_names = ', '.join(columns)
    update_set = ', '.join([f"{col} = EXCLUDED.{col}" for col in columns if col != 'team_id'])
    
    query = f"""
        INSERT INTO creator_teams ({column_names})
        VALUES ({placeholders})
        ON CONFLICT (team_id) DO UPDATE SET {update_set}
    """
    
    result = _execute_query(
        query,
        params=tuple(values),
        error_handler=_handle_st_error("upsert creator team", False),
    )
    return result is not False


def get_creator_teams() -> List[Dict]:
    """Retrieve all creator teams from the database."""
    return _execute_query(
        "SELECT * FROM creator_teams ORDER BY manager_name",
        use_dict_cursor=True,
        error_handler=_handle_st_error("get creator teams", []),
    )


def get_creator_team(team_id: int) -> Optional[Dict]:
    """Get a specific creator team by team_id."""
    return _execute_query(
        "SELECT * FROM creator_teams WHERE team_id = %s",
        params=(team_id,),
        use_dict_cursor=True,
        fetch_one=True,
        error_handler=_handle_st_error("get creator team", None),
    )


def get_current_creator_gameweek() -> Optional[int]:
    """Get the current gameweek from creator_teams table."""
    return _execute_query(
        "SELECT current_gameweek FROM creator_teams LIMIT 1",
        fetch_one=True,
        error_handler=_handle_st_debug("get current creator gameweek", None),
    )


def get_manager_by_id(manager_id: int) -> Optional[Dict]:
    """Get a manager by their manager_id."""
    return _execute_query(
        "SELECT manager_id, manager_name, team_name FROM all_managers WHERE manager_id = %s",
        params=(manager_id,),
        use_dict_cursor=True,
        fetch_one=True,
        error_handler=_handle_st_debug("get manager by ID", None),
    )


# Legacy function for compatibility
def get_client():
    """Legacy function for compatibility. Returns None as we use direct connections now."""
    return None
