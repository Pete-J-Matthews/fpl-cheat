#!/usr/bin/env python3
"""
Cron job script to update creator teams daily.
This script runs independently without Streamlit and logs to stdout/stderr.
"""

import sys
from datetime import datetime

from app.update_creator_teams import update_all_creator_teams


def log_progress(message: str):
    """Log progress messages to stdout with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {message}", flush=True)


def log_error(message: str):
    """Log error messages to stderr with timestamp."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] ERROR: {message}", file=sys.stderr, flush=True)


def main():
    """Main function to update creator teams."""
    log_progress("Starting creator teams update...")
    
    try:
        results = update_all_creator_teams(progress_callback=log_progress)
        
        if results.get("already_up_to_date", False):
            log_progress("Teams are already up to date")
            return 0
        
        success = results.get("success", 0)
        failed = results.get("failed", 0)
        total = results.get("total", 0)
        
        log_progress(f"Update complete: {success}/{total} successful, {failed} failed")
        
        if failed > 0:
            log_error(f"Failed to update {failed} team(s)")
            # Still return 0 if at least some teams were updated
            # Return 1 only if all teams failed
            return 1 if success == 0 else 0
        
        log_progress("All teams updated successfully")
        return 0
        
    except Exception as e:
        log_error(f"Fatal error during update: {e}")
        import traceback
        log_error(traceback.format_exc())
        return 1


if __name__ == "__main__":
    sys.exit(main())

