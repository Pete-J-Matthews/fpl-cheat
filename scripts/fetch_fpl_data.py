#!/usr/bin/env python3
"""
FPL Data Fetcher

Fetches manager data from the Fantasy Premier League API and stores it in the database.
Supports both local (SQLite) and production (PostgreSQL/Railway) environments.

Pages are fetched concurrently in windows. Concurrency ramps up to --max-workers and
halves whenever the API returns a throttling status, so the fetch self-limits rather
than guessing a safe delay. Progress is saved after every window and is resumable.

Usage:
    python scripts/fetch_fpl_data.py local
    python scripts/fetch_fpl_data.py production
    python scripts/fetch_fpl_data.py local --test          # Only fetch one page
    python scripts/fetch_fpl_data.py local --reset         # Delete all data and start fresh
    python scripts/fetch_fpl_data.py local --limit 5000    # Bounded run, for ramp testing
"""

import argparse
import logging
import os
import sqlite3
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

try:
    import psycopg2
    from psycopg2.extras import execute_values
except ImportError:
    psycopg2 = None
    execute_values = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

# FPL API Configuration
FPL_API_BASE = "https://fantasy.premierleague.com/api"
LEAGUE_ID = 314  # Overall league
STANDINGS_ENDPOINT = f"/leagues-classic/{LEAGUE_ID}/standings/"

# An identifiable client is less likely to be blocked than an anonymous one.
USER_AGENT = os.getenv(
    "FPL_USER_AGENT", "fpl-cheat/1.0 (personal FPL comparison app; contact via repo)"
)

# Concurrency: ramps from MIN to MAX, halves on any throttling response.
MIN_WORKERS = 4
DEFAULT_MAX_WORKERS = 8
WINDOW_PAGES = 2000  # Pages per save point
REQUEST_TIMEOUT = 30
MAX_RETRIES = 3
THROTTLE_STATUSES = {403, 429, 503}
DEFAULT_BACKOFF = 60  # Seconds to wait when throttled without a Retry-After

_local = threading.local()


class RateLimited(Exception):
    """The API asked us to slow down."""

    def __init__(self, page: int, status: int, retry_after: int):
        super().__init__(f"page {page}: HTTP {status}, retry after {retry_after}s")
        self.status = status
        self.retry_after = retry_after


def _session() -> requests.Session:
    """One pooled session per thread, for connection reuse."""
    if not hasattr(_local, "session"):
        _local.session = requests.Session()
        _local.session.headers["User-Agent"] = USER_AGENT
    return _local.session


def _retry_after(response: requests.Response) -> int:
    """Seconds to wait, taken from Retry-After when the server sends one."""
    try:
        return max(1, min(300, int(response.headers.get("Retry-After", ""))))
    except ValueError:
        return DEFAULT_BACKOFF


def parse_managers(data: dict | None, page: int) -> list[dict]:
    """Extract manager records from one standings page, skipping invalid rows."""
    managers = []
    for result in (data or {}).get("standings", {}).get("results", []):
        manager_id = result.get("entry")
        manager_name = result.get("player_name")
        team_name = result.get("entry_name")
        if not isinstance(manager_id, int) or isinstance(manager_id, bool):
            logger.warning(f"Page {page}: bad manager_id {manager_id!r}, skipping")
            continue
        if not isinstance(manager_name, str) or not manager_name.strip():
            logger.warning(f"Page {page}: bad manager_name {manager_name!r}, skipping")
            continue
        if not isinstance(team_name, str) or not team_name.strip():
            logger.warning(f"Page {page}: bad team_name {team_name!r}, skipping")
            continue
        managers.append(
            {
                "manager_id": manager_id,
                "manager_name": manager_name,
                "team_name": team_name,
            }
        )
    return managers


class FPLDataFetcher:
    """Fetches standings pages concurrently, backing off when throttled."""

    def fetch_page(self, page: int) -> dict | None:
        """Fetch one page. Returns None if it failed; raises RateLimited if throttled."""
        url = f"{FPL_API_BASE}{STANDINGS_ENDPOINT}?page_standings={page}"
        for attempt in range(MAX_RETRIES):
            if attempt:
                time.sleep(2**attempt)
            try:
                response = _session().get(url, timeout=REQUEST_TIMEOUT)
            except requests.RequestException as exc:
                logger.error(f"Page {page} attempt {attempt + 1} failed: {exc}")
                continue
            if response.status_code in THROTTLE_STATUSES:
                raise RateLimited(page, response.status_code, _retry_after(response))
            if response.status_code != 200:
                logger.error(f"Page {page} returned HTTP {response.status_code}")
                continue
            try:
                return response.json()
            except ValueError as exc:
                logger.error(f"Page {page} returned non-JSON: {exc}")
        return None

    def _has_rows(self, page: int) -> bool:
        """Whether a page holds rows. Raises rather than read a failure as the end."""
        data = self.fetch_page(page)
        if data is None:
            raise RuntimeError(f"Could not fetch page {page} while probing for the end")
        return bool(data.get("standings", {}).get("results", []))

    def find_last_page(self) -> int:
        """Binary search the deepest page that still returns rows."""
        if not self._has_rows(1):
            return 0
        low, high = 1, 1024
        while self._has_rows(high):
            low, high = high, high * 2
        while low + 1 < high:
            mid = (low + high) // 2
            if self._has_rows(mid):
                low = mid
            else:
                high = mid
        return low

    def fetch_window(self, pages: list[int], workers: int) -> dict[int, dict | None]:
        """Fetch pages concurrently, cancelling the rest if we get throttled."""
        results: dict[int, dict | None] = {}
        executor = ThreadPoolExecutor(max_workers=workers)
        futures = {executor.submit(self.fetch_page, page): page for page in pages}
        try:
            for future in as_completed(futures):
                results[futures[future]] = future.result()
            return results
        except RateLimited:
            executor.shutdown(wait=False, cancel_futures=True)
            raise
        finally:
            executor.shutdown(wait=True)

    def fetch_all_managers(
        self, start_page: int, last_page: int, db_manager, max_workers: int
    ) -> int:
        """Fetch start_page..last_page in windows, saving progress after each."""
        workers = min(MIN_WORKERS, max_workers)
        page = start_page
        while page <= last_page:
            window = list(range(page, min(page + WINDOW_PAGES, last_page + 1)))
            started = time.time()
            try:
                results = self.fetch_window(window, workers)
            except RateLimited as exc:
                workers = max(1, workers // 2)
                logger.warning(
                    f"Throttled (HTTP {exc.status}): sleeping {exc.retry_after}s, "
                    f"dropping to {workers} workers"
                )
                time.sleep(exc.retry_after)
                continue

            failed = [p for p in window if results.get(p) is None]
            if len(failed) > len(window) // 2:
                logger.error(
                    f"{len(failed)}/{len(window)} pages failed from {window[0]}, stopping"
                )
                break
            if failed:
                logger.warning(
                    f"{len(failed)} pages failed and were skipped: {failed[:10]}"
                )

            managers = [m for p in window for m in parse_managers(results[p], p)]
            db_manager.upsert_managers(managers)
            db_manager.update_progress(window[-1], len(managers))
            elapsed = time.time() - started
            logger.info(
                f"Pages {window[0]}-{window[-1]}: {len(managers):,} managers in "
                f"{elapsed:.1f}s ({len(window) / elapsed:.0f} pages/s, {workers} workers)"
            )

            page = window[-1] + 1
            if workers < max_workers:
                workers += 1
        return db_manager.get_manager_count()


class DatabaseManager:
    """Handles database operations for storing FPL manager data."""

    def __init__(self, environment: str):
        self.environment = environment
        self.is_postgres = environment == "production"
        self.param = "%s" if self.is_postgres else "?"
        self.connection = self._get_connection()
        self._init_table()

    def _get_connection(self):
        """Get database connection based on environment."""
        if self.environment == "local":
            logger.info("Using local SQLite database")
            return sqlite3.connect("fpl_cheat.db")
        elif self.environment == "production":
            logger.info("Using production PostgreSQL database (Railway)")
            if psycopg2 is None:
                raise ImportError(
                    "psycopg2 not available. Install with: pip install psycopg2-binary"
                )
            database_url = os.getenv("DATABASE_URL")
            if not database_url:
                raise ValueError(
                    "DATABASE_URL not found. Railway provides this automatically."
                )
            return psycopg2.connect(database_url)
        else:
            raise ValueError("Environment must be 'local' or 'production'")

    def _init_table(self):
        """Initialize the all_managers table and progress tracking."""
        cursor = self.connection.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS all_managers (
                manager_id INTEGER PRIMARY KEY,
                manager_name TEXT NOT NULL,
                team_name TEXT NOT NULL
            )
        """)

        if self.is_postgres:
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_all_managers_team_name ON all_managers(team_name)"
            )
            cursor.execute(
                "CREATE INDEX IF NOT EXISTS idx_all_managers_manager_name ON all_managers(manager_name)"
            )

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fetch_progress (
                id INTEGER PRIMARY KEY DEFAULT 1,
                last_page INTEGER DEFAULT 0,
                last_manager_count INTEGER DEFAULT 0,
                last_batch_start_time TEXT,
                last_batch_end_time TEXT,
                total_managers_fetched INTEGER DEFAULT 0,
                CONSTRAINT single_row CHECK (id = 1)
            )
        """)

        if self.is_postgres:
            cursor.execute(
                "INSERT INTO fetch_progress (id, last_page, last_manager_count, total_managers_fetched) VALUES (1, 0, 0, 0) ON CONFLICT (id) DO NOTHING"
            )
        else:
            cursor.execute(
                "INSERT OR IGNORE INTO fetch_progress (id, last_page, last_manager_count, total_managers_fetched) VALUES (1, 0, 0, 0)"
            )

        self.connection.commit()
        logger.info(
            f"Initialized tables in {'PostgreSQL' if self.is_postgres else 'SQLite'}"
        )

    def upsert_managers(self, managers: list[dict]) -> int:
        """Insert or update managers in the database."""
        if not managers:
            return 0

        cursor = self.connection.cursor()
        values = [
            (m["manager_id"], m["manager_name"], m["team_name"]) for m in managers
        ]

        if self.is_postgres:
            if execute_values is None:
                raise ImportError("psycopg2.extras.execute_values not available")
            chunk_size = 500
            total = 0
            for i in range(0, len(values), chunk_size):
                chunk = values[i : i + chunk_size]
                try:
                    execute_values(
                        cursor,
                        """
                        INSERT INTO all_managers (manager_id, manager_name, team_name) VALUES %s
                        ON CONFLICT (manager_id) DO UPDATE SET manager_name = EXCLUDED.manager_name, team_name = EXCLUDED.team_name
                    """,
                        chunk,
                        page_size=chunk_size,
                    )
                    self.connection.commit()
                    total += len(chunk)
                except Exception as e:
                    logger.error(
                        f"Failed to upsert chunk {i}-{i + len(chunk) - 1}: {e}"
                    )
                    self.connection.rollback()
            return total
        else:
            cursor.executemany(
                "INSERT OR REPLACE INTO all_managers (manager_id, manager_name, team_name) VALUES (?, ?, ?)",
                values,
            )
            self.connection.commit()
            return len(managers)

    def get_manager_count(self) -> int:
        """Get the current number of managers in the database."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM all_managers")
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Failed to get manager count: {e}")
            return 0

    def get_progress(self) -> dict:
        """Get the current progress state."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM fetch_progress WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return {
                    "last_page": row[1],
                    "last_manager_count": row[2],
                    "last_batch_start_time": row[3],
                    "last_batch_end_time": row[4],
                    "total_managers_fetched": row[5],
                }
            return {
                "last_page": 0,
                "last_manager_count": 0,
                "total_managers_fetched": 0,
            }
        except Exception as e:
            logger.error(f"Failed to get progress: {e}")
            return {
                "last_page": 0,
                "last_manager_count": 0,
                "total_managers_fetched": 0,
            }

    def update_progress(
        self,
        last_page: int,
        last_manager_count: int,
        batch_start_time: str | None = None,
        batch_end_time: str | None = None,
    ):
        """Update the progress state."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM all_managers")
            total_managers = cursor.fetchone()[0]
            cursor.execute(
                f"""
                UPDATE fetch_progress
                SET last_page = {self.param}, last_manager_count = {self.param},
                    last_batch_start_time = COALESCE({self.param}, last_batch_start_time),
                    last_batch_end_time = COALESCE({self.param}, last_batch_end_time),
                    total_managers_fetched = {self.param}
                WHERE id = 1
            """,
                (
                    last_page,
                    last_manager_count,
                    batch_start_time,
                    batch_end_time,
                    total_managers,
                ),
            )
            self.connection.commit()
        except Exception as e:
            logger.error(f"Failed to update progress: {e}")
            if self.connection:
                self.connection.rollback()

    def delete_all_managers(self):
        """Delete all rows from the all_managers table."""
        try:
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM all_managers")
            deleted_count = cursor.fetchone()[0]
            if deleted_count == 0:
                logger.info("No rows to delete")
                return 0
            cursor.execute("DELETE FROM all_managers")
            self.connection.commit()
            logger.info(f"Deleted {deleted_count} rows")
            return deleted_count
        except Exception as e:
            logger.error(f"Failed to delete managers: {e}")
            if self.connection:
                self.connection.rollback()
            return 0

    def reset_progress(self):
        """Reset the fetch progress to initial state."""
        try:
            cursor = self.connection.cursor()
            cursor.execute(
                "UPDATE fetch_progress SET last_page = 0, last_manager_count = 0, last_batch_start_time = NULL, last_batch_end_time = NULL, total_managers_fetched = 0 WHERE id = 1"
            )
            self.connection.commit()
            logger.info("Reset fetch progress")
        except Exception as e:
            logger.error(f"Failed to reset progress: {e}")
            if self.connection:
                self.connection.rollback()

    def close(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()


def main():
    """Main function to run the FPL data fetcher."""
    parser = argparse.ArgumentParser(
        description="Fetch FPL manager data and store in database"
    )
    parser.add_argument(
        "environment",
        choices=["local", "production"],
        help="Database environment to use",
    )
    parser.add_argument(
        "--test", action="store_true", help="Test mode: only fetch one page"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all rows from all_managers table and reset progress before fetching",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f"Concurrency ceiling (default {DEFAULT_MAX_WORKERS})",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Stop after this many pages, for ramp testing",
    )

    args = parser.parse_args()
    logger.info(f"Starting FPL data fetch for {args.environment} environment")

    try:
        db_manager = DatabaseManager(args.environment)

        if args.reset:
            logger.warning("RESET MODE: deleting all rows from all_managers...")
            deleted_count = db_manager.delete_all_managers()
            db_manager.reset_progress()
            logger.info(f"Deleted {deleted_count} rows and reset progress")

        logger.info(f"Initial manager count: {db_manager.get_manager_count():,}")
        progress = db_manager.get_progress()
        start_page = 1 if args.reset else max(1, progress["last_page"] + 1)
        fetcher = FPLDataFetcher()

        if args.test:
            managers = parse_managers(fetcher.fetch_page(start_page), start_page)[:5]
            logger.info(
                f"Test mode: found {len(managers)} managers on page {start_page}"
            )
            if managers:
                logger.info(
                    f"Test mode: inserted {db_manager.upsert_managers(managers)}"
                )
            db_manager.close()
            return

        last_page = fetcher.find_last_page()
        if args.limit:
            last_page = min(last_page, start_page + args.limit - 1)
        logger.info(
            f"Fetching pages {start_page}-{last_page:,} (max {args.max_workers} workers)"
        )

        if start_page > last_page:
            logger.info("Nothing to fetch. Reset last_page to refetch from the start.")
            db_manager.close()
            return

        start_time = time.strftime("%Y-%m-%d %H:%M:%S")
        total = fetcher.fetch_all_managers(
            start_page, last_page, db_manager, args.max_workers
        )
        db_manager.update_progress(
            db_manager.get_progress()["last_page"],
            0,
            start_time,
            time.strftime("%Y-%m-%d %H:%M:%S"),
        )
        logger.info(f"Total managers in database: {total:,}")
        db_manager.close()
        logger.info("FPL data fetch completed successfully")

    except KeyboardInterrupt:
        logger.info("Interrupted. Progress was saved after the last completed window.")
        sys.exit(0)
    except Exception as exc:
        logger.error(f"Fatal error: {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
