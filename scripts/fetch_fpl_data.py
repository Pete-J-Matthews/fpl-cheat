#!/usr/bin/env python3
"""
FPL Data Fetcher

Fetches manager data from the Fantasy Premier League API into the Postgres database
named by DATABASE_URL. Locally that is the throwaway container from the deploy-local
skill; in Railway it is provided automatically.

Pages are fetched concurrently in windows. Concurrency ramps up to --max-workers and
halves whenever the API returns a throttling status, so the fetch self-limits rather
than guessing a safe delay. Progress is saved after every window and is resumable.

Usage:
    python scripts/fetch_fpl_data.py
    python scripts/fetch_fpl_data.py --test          # Only fetch one page
    python scripts/fetch_fpl_data.py --reset         # Delete all data and start fresh
    python scripts/fetch_fpl_data.py --limit 5000    # Bounded run, for ramp testing
"""

import argparse
import logging
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import psycopg2
import requests
from psycopg2.extras import execute_values

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
UPSERT_CHUNK = 500  # Rows per execute_values batch

_local = threading.local()


def _database_url() -> str:
    """The Postgres DSN to write to."""
    url = os.getenv("DATABASE_URL")
    if not url:
        raise ValueError("DATABASE_URL is not set")
    return url


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
            written = db_manager.upsert_managers(managers)
            if written != len(managers):
                raise RuntimeError(
                    f"Wrote {written} of {len(managers)} managers, leaving the "
                    f"watermark at {window[0] - 1} so the window is retried"
                )
            db_manager.set_last_page(window[-1])
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
    """Stores FPL manager data in the Postgres database named by DATABASE_URL."""

    def __init__(self):
        self.connection = psycopg2.connect(_database_url())
        self._init_tables()

    def _init_tables(self):
        """Create the manager and progress tables if they do not exist yet."""
        cursor = self.connection.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS all_managers (
                manager_id INTEGER PRIMARY KEY,
                manager_name TEXT NOT NULL,
                team_name TEXT NOT NULL
            )
        """)
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_all_managers_team_name ON all_managers(team_name)"
        )
        cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_all_managers_manager_name ON all_managers(manager_name)"
        )
        # Deployed databases carry extra unused columns here; they are left alone.
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fetch_progress (
                id INTEGER PRIMARY KEY DEFAULT 1,
                last_page INTEGER DEFAULT 0,
                CONSTRAINT single_row CHECK (id = 1)
            )
        """)
        cursor.execute(
            "INSERT INTO fetch_progress (id, last_page) VALUES (1, 0) ON CONFLICT (id) DO NOTHING"
        )
        self.connection.commit()

    def upsert_managers(self, managers: list[dict]) -> int:
        """Insert or update managers. Raises on failure so the caller can stop."""
        if not managers:
            return 0
        cursor = self.connection.cursor()
        values = [
            (m["manager_id"], m["manager_name"], m["team_name"]) for m in managers
        ]
        for i in range(0, len(values), UPSERT_CHUNK):
            execute_values(
                cursor,
                """
                INSERT INTO all_managers (manager_id, manager_name, team_name) VALUES %s
                ON CONFLICT (manager_id) DO UPDATE SET
                    manager_name = EXCLUDED.manager_name, team_name = EXCLUDED.team_name
            """,
                values[i : i + UPSERT_CHUNK],
                page_size=UPSERT_CHUNK,
            )
            self.connection.commit()
        return len(values)

    def get_manager_count(self) -> int:
        """Number of managers currently stored."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT COUNT(*) FROM all_managers")
        return cursor.fetchone()[0]

    def get_last_page(self) -> int:
        """The last fully fetched page. Raises rather than reporting a false zero."""
        cursor = self.connection.cursor()
        cursor.execute("SELECT last_page FROM fetch_progress WHERE id = 1")
        row = cursor.fetchone()
        return row[0] if row else 0

    def set_last_page(self, last_page: int):
        """Advance the resume watermark."""
        cursor = self.connection.cursor()
        cursor.execute(
            "UPDATE fetch_progress SET last_page = %s WHERE id = 1", (last_page,)
        )
        self.connection.commit()

    def delete_all_managers(self) -> int:
        """Delete every row from all_managers, returning how many went."""
        cursor = self.connection.cursor()
        cursor.execute("DELETE FROM all_managers")
        self.connection.commit()
        return cursor.rowcount

    def close(self):
        """Close the database connection."""
        if self.connection:
            self.connection.close()


def main():
    """Fetch FPL manager data into the database named by DATABASE_URL."""
    parser = argparse.ArgumentParser(
        description="Fetch FPL manager data and store it in Postgres"
    )
    parser.add_argument(
        "--test", action="store_true", help="Test mode: only fetch one page"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Delete all rows from all_managers and refetch from page 1",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=DEFAULT_MAX_WORKERS,
        help=f"Concurrency ceiling (default {DEFAULT_MAX_WORKERS})",
    )
    parser.add_argument(
        "--limit", type=int, help="Stop after this many pages, for ramp testing"
    )
    args = parser.parse_args()

    try:
        db_manager = DatabaseManager()

        if args.reset:
            logger.warning("RESET MODE: deleting all rows from all_managers...")
            deleted = db_manager.delete_all_managers()
            db_manager.set_last_page(0)
            logger.info(f"Deleted {deleted:,} rows and reset the watermark")

        logger.info(f"Initial manager count: {db_manager.get_manager_count():,}")
        start_page = max(1, db_manager.get_last_page() + 1)
        fetcher = FPLDataFetcher()

        if args.test:
            managers = parse_managers(fetcher.fetch_page(start_page), start_page)[:5]
            logger.info(f"Test mode: {len(managers)} managers on page {start_page}")
            if managers:
                logger.info(
                    f"Test mode: upserted {db_manager.upsert_managers(managers)}"
                )
            db_manager.close()
            return

        last_page = fetcher.find_last_page()
        if args.limit:
            last_page = min(last_page, start_page + args.limit - 1)
        if start_page > last_page:
            logger.info(
                "Nothing to fetch. Reset last_page in fetch_progress to start again."
            )
            db_manager.close()
            return

        logger.info(
            f"Fetching pages {start_page:,}-{last_page:,} (up to {args.max_workers} workers)"
        )
        total = fetcher.fetch_all_managers(
            start_page, last_page, db_manager, args.max_workers
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
