#!/usr/bin/env python3
"""
FPL Data Fetcher

Fetches manager data from the Fantasy Premier League API and stores it in the database.
Supports both local (SQLite) and production (Supabase) environments.
Runs continuously until all data is fetched, rate limited, or manually stopped.
Progress is automatically saved at regular intervals.

Usage:
    python scripts/fetch_fpl_data.py local
    python scripts/fetch_fpl_data.py production
    python scripts/fetch_fpl_data.py local --test    # Test mode: only fetch first page
"""

import argparse
import json
import logging
import os
import random
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

# Database imports
import sqlite3
try:
    from supabase import create_client, Client as SupabaseClient
except ImportError:
    SupabaseClient = None

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# FPL API Configuration
FPL_API_BASE = "https://fantasy.premierleague.com/api"
LEAGUE_ID = 314  # Overall league
STANDINGS_ENDPOINT = f"/leagues-classic/{LEAGUE_ID}/standings/"

# Rate limiting configuration
MIN_DELAY = 0.5  # Minimum delay between requests (seconds)
MAX_DELAY = 1.6  # Maximum delay between requests (seconds)
MAX_RETRIES = 3  # Maximum number of retries for failed requests

# Processing configuration
PROGRESS_SAVE_INTERVAL = 50  # Save progress every N pages


class FPLDataFetcher:
    """Handles fetching data from the FPL API with rate limiting and error handling."""
    
    def __init__(self):
        self.total_managers = 0
        self.processed_managers = 0
    
    def _random_delay(self):
        """Add a random delay to avoid rate limiting."""
        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        logger.debug(f"Waiting {delay:.2f} seconds before next request...")
        time.sleep(delay)
    
    def fetch_page_curl(self, page: int) -> Optional[Dict]:
        """Fetch a single page using curl with retry logic."""
        url = f"{FPL_API_BASE}{STANDINGS_ENDPOINT}?page_standings={page}"
        
        for attempt in range(MAX_RETRIES):
            try:
                if attempt > 0:
                    logger.info(f"Retry attempt {attempt + 1} for page {page}...")
                    # Exponential backoff
                    time.sleep(2 ** attempt)
                
                logger.info(f"Fetching page {page} using curl...")
                
                # Use curl to fetch the data
                result = subprocess.run(
                    ['curl', '-s', '--max-time', '30', url],
                    capture_output=True,
                    text=True,
                    timeout=35
                )
                
                if result.returncode != 0:
                    logger.error(f"Curl failed with return code {result.returncode}")
                    logger.error(f"Curl stderr: {result.stderr}")
                    if attempt == MAX_RETRIES - 1:
                        return None
                    continue
                
                if not result.stdout:
                    logger.error(f"Empty response for page {page}")
                    if attempt == MAX_RETRIES - 1:
                        return None
                    continue
                
                # Try to parse as JSON
                data = json.loads(result.stdout)
                logger.debug(f"Successfully fetched page {page} using curl")
                return data
                
            except subprocess.TimeoutExpired:
                logger.error(f"Curl timeout for page {page} (attempt {attempt + 1})")
                if attempt == MAX_RETRIES - 1:
                    return None
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON for page {page}: {e}")
                logger.error(f"Response content (first 200 chars): {result.stdout[:200]}")
                if attempt == MAX_RETRIES - 1:
                    return None
            except Exception as e:
                logger.error(f"Unexpected error fetching page {page}: {e}")
                if attempt == MAX_RETRIES - 1:
                    return None
        
        return None

    def fetch_page(self, page: int) -> Optional[Dict]:
        """Fetch a single page of standings data."""
        # Try curl method first since requests seems to be blocked
        return self.fetch_page_curl(page)
    
    def fetch_all_managers(self, start_page: int, db_manager=None) -> Tuple[List[Dict], int, bool]:
        """
        Fetch all available managers starting from a specific page.
        Continues until no more pages are available or rate limited.
        
        Args:
            start_page: Page number to start from
            db_manager: Database manager for progress updates (optional)
            
        Returns:
            Tuple of (managers_list, last_page_processed, has_more_pages)
        """
        all_managers = []
        page = start_page
        has_more_pages = True
        consecutive_failures = 0
        max_consecutive_failures = 5  # Stop after 5 consecutive failures
        
        logger.info(f"Starting continuous fetch from page {start_page}...")
        logger.info(f"Will save progress every {PROGRESS_SAVE_INTERVAL} pages")
        
        while has_more_pages and consecutive_failures < max_consecutive_failures:
            # Add random delay before each request
            if page > start_page:
                self._random_delay()
            
            data = self.fetch_page(page)
            if not data:
                consecutive_failures += 1
                logger.error(f"Failed to fetch page {page} (failure #{consecutive_failures}/{max_consecutive_failures})")
                
                if consecutive_failures >= max_consecutive_failures:
                    logger.error(f"Too many consecutive failures ({consecutive_failures}), stopping...")
                    break
                continue
            
            # Reset failure counter on successful fetch
            consecutive_failures = 0
            
            standings = data.get('standings', {})
            results = standings.get('results', [])
            
            if not results:
                logger.info(f"No more results on page {page}, fetch complete...")
                has_more_pages = False
                break
            
            # Extract only the required fields
            page_managers = []
            for result in results:
                manager_data = {
                    'manager_id': result.get('id'),
                    'manager_name': result.get('player_name'),
                    'team_name': result.get('entry_name')
                }
                
                # Skip if any required field is missing
                if not all(manager_data.values()):
                    logger.warning(f"Skipping incomplete record: {manager_data}")
                    continue
                
                page_managers.append(manager_data)
            
            all_managers.extend(page_managers)
            self.processed_managers += len(page_managers)
            
            logger.info(f"Fetched page {page}: {len(page_managers)} managers (Total: {len(all_managers)})")
            
            # Save progress at regular intervals to prevent data loss
            if db_manager and page % PROGRESS_SAVE_INTERVAL == 0:
                logger.info(f"💾 Saving progress at page {page}...")
                inserted = db_manager.upsert_managers(all_managers)
                db_manager.update_progress(page, len(all_managers))
                logger.info(f"✅ Progress saved: {inserted:,} managers in database")
                # Clear the list to free memory, but keep track of total
                all_managers = []
            
            # Check if there are more pages
            if not standings.get('has_next', False):
                logger.info("No more pages available")
                has_more_pages = False
                break
            
            page += 1
        
        # Save any remaining managers
        if all_managers and db_manager:
            logger.info(f"💾 Saving final batch of {len(all_managers)} managers...")
            inserted = db_manager.upsert_managers(all_managers)
            db_manager.update_progress(page, len(all_managers))
            logger.info(f"✅ Final progress saved: {inserted:,} managers in database")
        
        logger.info(f"Fetch complete. Processed pages {start_page}-{page}")
        return all_managers, page, has_more_pages


class DatabaseManager:
    """Handles database operations for storing FPL manager data."""
    
    def __init__(self, environment: str):
        self.environment = environment
        self.connection = self._get_connection()
        self._init_table()
    
    def _get_connection(self):
        """Get database connection based on environment."""
        if self.environment == "local":
            logger.info("Using local SQLite database")
            return sqlite3.connect("fpl_cheat.db")
        elif self.environment == "production":
            logger.info("Using production Supabase database")
            if SupabaseClient is None:
                raise ImportError("Supabase client not available. Install with: pip install supabase")
            
            # Get Supabase credentials from environment or config
            url = self._get_supabase_url()
            key = self._get_supabase_key()
            
            self.client = create_client(url, key)
            return None  # Supabase doesn't use traditional connections
        else:
            raise ValueError("Environment must be 'local' or 'production'")
    
    def _get_supabase_url(self) -> str:
        """Get Supabase URL from environment or config."""
        # Try environment variable first
        url = os.getenv('SUPABASE_URL')
        if url:
            return url
        
        # Try Streamlit secrets
        try:
            import streamlit as st
            if "supabase" in st.secrets:
                return st.secrets["supabase"]["url"]
        except Exception:
            pass
        
        # Try reading secrets.toml directly
        try:
            import toml
            secrets_path = os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')
            if os.path.exists(secrets_path):
                with open(secrets_path, 'r') as f:
                    secrets = toml.load(f)
                    if 'supabase' in secrets and 'url' in secrets['supabase']:
                        return secrets['supabase']['url']
        except Exception as e:
            logger.debug(f"Failed to read secrets.toml: {e}")
        
        raise ValueError("Supabase URL not found. Set SUPABASE_URL environment variable or configure Streamlit secrets.")
    
    def _get_supabase_key(self) -> str:
        """Get Supabase key from environment or config."""
        # Try environment variable first
        key = os.getenv('SUPABASE_KEY')
        if key:
            return key
        
        # Try Streamlit secrets
        try:
            import streamlit as st
            if "supabase" in st.secrets:
                return st.secrets["supabase"]["key"]
        except Exception:
            pass
        
        # Try reading secrets.toml directly
        try:
            import toml
            secrets_path = os.path.join(os.path.dirname(__file__), '.streamlit', 'secrets.toml')
            if os.path.exists(secrets_path):
                with open(secrets_path, 'r') as f:
                    secrets = toml.load(f)
                    if 'supabase' in secrets and 'key' in secrets['supabase']:
                        return secrets['supabase']['key']
        except Exception as e:
            logger.debug(f"Failed to read secrets.toml: {e}")
        
        raise ValueError("Supabase key not found. Set SUPABASE_KEY environment variable or configure Streamlit secrets.")
    
    def _init_table(self):
        """Initialize the all_managers table and progress tracking."""
        if self.environment == "local":
            cursor = self.connection.cursor()
            
            # Create all_managers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS all_managers (
                    manager_id INTEGER PRIMARY KEY,
                    manager_name TEXT,
                    team_name TEXT
                )
            """)
            
            # Create progress tracking table
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
            
            # Insert initial progress record if it doesn't exist
            cursor.execute("""
                INSERT OR IGNORE INTO fetch_progress (id, last_page, last_manager_count, total_managers_fetched)
                VALUES (1, 0, 0, 0)
            """)
            
            self.connection.commit()
            logger.info("Initialized all_managers and fetch_progress tables in SQLite")
        else:
            # For Supabase, we assume the tables already exist
            logger.info("Using existing all_managers and fetch_progress tables in Supabase")
    
    def upsert_managers(self, managers: List[Dict]) -> int:
        """Insert or update managers in the database."""
        if not managers:
            return 0
        
        if self.environment == "local":
            return self._upsert_sqlite(managers)
        else:
            return self._upsert_supabase(managers)
    
    def _upsert_sqlite(self, managers: List[Dict]) -> int:
        """Upsert managers in SQLite database."""
        cursor = self.connection.cursor()
        
        # Use INSERT OR REPLACE for upsert behavior
        cursor.executemany("""
            INSERT OR REPLACE INTO all_managers (manager_id, manager_name, team_name)
            VALUES (?, ?, ?)
        """, [(m['manager_id'], m['manager_name'], m['team_name']) for m in managers])
        
        self.connection.commit()
        return len(managers)
    
    def _upsert_supabase(self, managers: List[Dict]) -> int:
        """Upsert managers in Supabase database."""
        try:
            # Chunk large payloads to avoid statement timeouts
            chunk_size = 500
            total = 0
            for i in range(0, len(managers), chunk_size):
                chunk = managers[i:i + chunk_size]
                try:
                    self.client.table('all_managers').upsert(
                        chunk,
                        on_conflict='manager_id'
                    ).execute()
                    total += len(chunk)
                except Exception as chunk_err:
                    logger.error(f"Failed to upsert managers chunk ({i}-{i+len(chunk)-1}) in Supabase: {chunk_err}")
                    # Continue with next chunk rather than failing the whole batch
                    continue
            return total
        except Exception as e:
            logger.error(f"Failed to upsert managers in Supabase: {e}")
            return 0
    
    def get_manager_count(self) -> int:
        """Get the current number of managers in the database."""
        if self.environment == "local":
            cursor = self.connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM all_managers")
            return cursor.fetchone()[0]
        else:
            try:
                result = self.client.table('all_managers').select('manager_id', count='exact').execute()
                return result.count
            except Exception as e:
                logger.error(f"Failed to get manager count from Supabase: {e}")
                return 0
    
    def get_progress(self) -> Dict:
        """Get the current progress state."""
        if self.environment == "local":
            cursor = self.connection.cursor()
            cursor.execute("SELECT * FROM fetch_progress WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return {
                    'last_page': row[1],
                    'last_manager_count': row[2],
                    'last_batch_start_time': row[3],
                    'last_batch_end_time': row[4],
                    'total_managers_fetched': row[5]
                }
            return {'last_page': 0, 'last_manager_count': 0, 'total_managers_fetched': 0}
        else:
            try:
                result = self.client.table('fetch_progress').select('*').eq('id', 1).execute()
                if result.data:
                    return result.data[0]
                return {'last_page': 0, 'last_manager_count': 0, 'total_managers_fetched': 0}
            except Exception as e:
                logger.error(f"Failed to get progress from Supabase: {e}")
                return {'last_page': 0, 'last_manager_count': 0, 'total_managers_fetched': 0}
    
    def update_progress(self, last_page: int, last_manager_count: int, 
                       batch_start_time: str = None, batch_end_time: str = None):
        """Update the progress state."""
        if self.environment == "local":
            cursor = self.connection.cursor()
            
            # Get current total
            cursor.execute("SELECT COUNT(*) FROM all_managers")
            total_managers = cursor.fetchone()[0]
            
            cursor.execute("""
                UPDATE fetch_progress 
                SET last_page = ?, 
                    last_manager_count = ?, 
                    last_batch_start_time = COALESCE(?, last_batch_start_time),
                    last_batch_end_time = COALESCE(?, last_batch_end_time),
                    total_managers_fetched = ?
                WHERE id = 1
            """, (last_page, last_manager_count, batch_start_time, batch_end_time, total_managers))
            
            self.connection.commit()
        else:
            try:
                # Get current total
                result = self.client.table('all_managers').select('manager_id', count='exact').execute()
                total_managers = result.count
                
                update_data = {
                    'last_page': last_page,
                    'last_manager_count': last_manager_count,
                    'total_managers_fetched': total_managers
                }
                
                if batch_start_time:
                    update_data['last_batch_start_time'] = batch_start_time
                if batch_end_time:
                    update_data['last_batch_end_time'] = batch_end_time
                
                self.client.table('fetch_progress').update(update_data).eq('id', 1).execute()
            except Exception as e:
                logger.error(f"Failed to update progress in Supabase: {e}")
    
    def close(self):
        """Close database connection."""
        if self.environment == "local" and self.connection:
            self.connection.close()



def main():
    """Main function to run the FPL data fetcher."""
    parser = argparse.ArgumentParser(description='Fetch FPL manager data and store in database')
    parser.add_argument('environment', choices=['local', 'production'], 
                       help='Database environment to use')
    parser.add_argument('--test', action='store_true', 
                       help='Test mode: only fetch first page')
    
    args = parser.parse_args()
    
    logger.info(f"Starting FPL data fetch for {args.environment} environment")
    
    try:
        # Initialize database
        db_manager = DatabaseManager(args.environment)
        initial_count = db_manager.get_manager_count()
        logger.info(f"Initial manager count: {initial_count}")
        
        # Get progress state
        progress = db_manager.get_progress()
        start_page = progress['last_page'] + 1 if progress['last_page'] > 0 else 1
        
        logger.info(f"Resuming from page {start_page}")
        logger.info(f"Previous progress: {progress['total_managers_fetched']} managers fetched")
        
        # Initialize fetcher
        fetcher = FPLDataFetcher()
        
        if args.test:
            logger.info(f"TEST MODE: Fetching page {start_page} (resume page)")
            data = fetcher.fetch_page(start_page)
            if data:
                standings = data.get('standings', {})
                results = standings.get('results', [])
                managers = []
                for result in results[:5]:  # Only take first 5 for testing
                    manager_data = {
                        'manager_id': result.get('id'),
                        'manager_name': result.get('player_name'),
                        'team_name': result.get('entry_name')
                    }
                    if all(manager_data.values()):
                        managers.append(manager_data)
                
                logger.info(f"Test mode: Found {len(managers)} managers in first page")
                if managers:
                    inserted = db_manager.upsert_managers(managers)
                    logger.info(f"Test mode: Inserted {inserted} managers")
            else:
                logger.error("Test mode: Failed to fetch first page")
        else:
            # Continuous fetch mode
            logger.info(f"\n🚀 Starting continuous fetch from page {start_page}")
            logger.info("📊 Will fetch all available managers until completion or rate limit")
            
            # Record start time
            start_time = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Fetch all managers
            managers, last_page, has_more_pages = fetcher.fetch_all_managers(
                start_page, db_manager
            )
            
            # Record end time
            end_time = time.strftime('%Y-%m-%d %H:%M:%S')
            
            # Update final progress
            db_manager.update_progress(
                last_page, len(managers), start_time, end_time
            )
            
            final_count = db_manager.get_manager_count()
            logger.info(f"📈 Total managers in database: {final_count:,}")
            
            if has_more_pages:
                logger.info("🎉 Fetch completed due to rate limiting or consecutive failures")
            else:
                logger.info("🎉 All pages processed! Data fetch complete.")
        
        db_manager.close()
        logger.info("✅ FPL data fetch completed successfully")
        
    except KeyboardInterrupt:
        logger.info("⏹️  Process interrupted by user. Saving progress...")
        try:
            # Try to save any remaining progress
            if 'db_manager' in locals():
                progress = db_manager.get_progress()
                logger.info(f"💾 Final progress saved: {progress['total_managers_fetched']} managers")
                db_manager.close()
        except Exception as e:
            logger.error(f"Failed to save progress on interrupt: {e}")
        logger.info("👋 Process stopped by user. Progress has been saved.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"💥 Fatal error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import os
    main()
