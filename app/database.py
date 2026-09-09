"""
PostgreSQL database helpers for searching FPL managers in production DB.
Uses Railway PostgreSQL database via DATABASE_URL from environment variable.
"""

import logging
import os
import re
from collections.abc import Callable
from contextlib import contextmanager
from typing import Any

import psycopg2
import streamlit as st
from psycopg2.extras import RealDictCursor

logger = logging.getLogger(__name__)


class DatabaseTimeoutError(Exception):
    """A query exceeded the database's statement timeout."""


def get_database_url() -> str:
    """Return DATABASE_URL from environment variables."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise RuntimeError(
            "Database credentials missing. Set DATABASE_URL environment variable. "
            "Railway automatically provides this when you add a PostgreSQL service."
        )
    return database_url


@contextmanager
def get_connection():
    """Context manager for PostgreSQL connections."""
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
    error_handler: Callable[[Exception], Any] | None = None,
) -> Any:
    """Run a query. Writes return whether any row was affected; reads return rows."""
    try:
        with get_connection() as conn:
            cursor = conn.cursor(
                cursor_factory=RealDictCursor if use_dict_cursor else None
            )
            cursor.execute(query, params)

            # DBAPI leaves description unset for statements with no result set (INSERT/UPDATE/DELETE).
            if cursor.description is None:
                return cursor.rowcount > 0

            if not fetch_one:
                rows = cursor.fetchall()
                return [dict(row) for row in rows] if use_dict_cursor else rows

            row = cursor.fetchone()
            if use_dict_cursor:
                return dict(row) if row else row
            return row[0] if row else row
    except Exception as e:
        if error_handler:
            return error_handler(e)
        raise


def _handle_timeout_error(e: Exception) -> None:
    """Re-raise a statement timeout with search advice; anything else unchanged."""
    if "timeout" in str(e).lower() or "57014" in str(e):
        raise DatabaseTimeoutError(
            "Database query timed out. The database may be under heavy load. "
            "Please try:\n"
            "1. Using a longer/more specific search term (at least 4 characters)\n"
            "2. Entering your manager ID directly (numbers only)\n"
            "3. Trying again in a few moments"
        ) from e
    # Called from inside an except block, so this re-raises the original.
    raise e


def _report(operation: str, default: Any = None, quiet: bool = False):
    """Error handler that surfaces the failure and returns a default instead of raising."""

    def handler(e: Exception) -> Any:
        if quiet:
            logger.warning("Failed to %s: %s", operation, e)
        else:
            st.error(f"Failed to {operation}: {e}")
        return default

    return handler


def search_managers(query: str) -> list[dict]:
    """Search `all_managers` by manager_name or team_name using case-insensitive prefix match."""
    q = query.strip()
    if len(q) < 4:
        return []

    # Escaped so a literal % or _ cannot widen the prefix into a full-table scan.
    pattern = re.sub(r"([\\%_])", r"\\\1", q.lower()) + "%"
    # No DISTINCT: manager_id is the PK, and it would block the LIMIT from stopping early.
    return _execute_query(
        """
        SELECT manager_id, manager_name, team_name
        FROM all_managers
        WHERE lower(manager_name) LIKE %s OR lower(team_name) LIKE %s
        LIMIT 50
        """,
        params=(pattern, pattern),
        use_dict_cursor=True,
        error_handler=_handle_timeout_error,
    )


def upsert_creator_team(team_data: dict) -> bool:
    """Insert or update a creator team in the creator_teams table."""
    columns = list(team_data)
    update_set = ", ".join(
        f"{col} = EXCLUDED.{col}" for col in columns if col != "team_id"
    )
    result = _execute_query(
        f"""
        INSERT INTO creator_teams ({", ".join(columns)})
        VALUES ({", ".join(["%s"] * len(columns))})
        ON CONFLICT (team_id) DO UPDATE SET {update_set}
        """,
        params=tuple(team_data[col] for col in columns),
        error_handler=_report("upsert creator team", False),
    )
    return result is not False


def get_creator_teams() -> list[dict]:
    """Retrieve all creator teams from the database."""
    return _execute_query(
        "SELECT * FROM creator_teams ORDER BY manager_name",
        use_dict_cursor=True,
        error_handler=_report("get creator teams", []),
    )


def get_current_creator_gameweek() -> int | None:
    """Get the current gameweek from creator_teams table."""
    return _execute_query(
        "SELECT current_gameweek FROM creator_teams LIMIT 1",
        fetch_one=True,
        error_handler=_report("get current creator gameweek", None, quiet=True),
    )


def get_manager_by_id(manager_id: int) -> dict | None:
    """Get a manager by their manager_id."""
    return _execute_query(
        "SELECT manager_id, manager_name, team_name FROM all_managers WHERE manager_id = %s",
        params=(manager_id,),
        use_dict_cursor=True,
        fetch_one=True,
        error_handler=_report("get manager by ID", None, quiet=True),
    )
