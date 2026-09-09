#!/usr/bin/env python3
"""
Cron job script to update creator teams daily.
This script runs independently without Streamlit and logs to stdout/stderr.
"""

import sys
import traceback
from datetime import datetime
from zoneinfo import ZoneInfo

from app.update_creator_teams import update_all_creator_teams

UK = ZoneInfo("Europe/London")


def log(message: str, stream=sys.stdout) -> None:
    """Log a timestamped message. Errors go to stderr so the cron host can split them."""
    print(f"[{datetime.now(UK):%Y-%m-%d %H:%M:%S}] {message}", file=stream, flush=True)


def main() -> int:
    """Update creator teams. Exits non-zero only when nothing at all was updated."""
    log("Starting creator teams update...")
    try:
        results = update_all_creator_teams(progress_callback=log)
    except Exception as exc:
        log(f"ERROR: Fatal error during update: {exc}", sys.stderr)
        log(f"ERROR: {traceback.format_exc()}", sys.stderr)
        return 1

    if results["already_up_to_date"]:
        log("Teams are already up to date")
        return 0

    success, failed, total = results["success"], results["failed"], results["total"]
    log(f"Update complete: {success}/{total} successful, {failed} failed")
    if not failed:
        log("All teams updated successfully")
        return 0

    log(f"ERROR: Failed to update {failed} team(s)", sys.stderr)
    # A partial success is still progress; only a total failure is worth a non-zero exit.
    return 1 if success == 0 else 0


if __name__ == "__main__":
    sys.exit(main())
