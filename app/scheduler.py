"""Background scheduler for updating creator teams at 5pm and midnight UK time."""

import logging
import threading
from zoneinfo import ZoneInfo

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.update_creator_teams import update_all_creator_teams

logger = logging.getLogger(__name__)
UK_TZ = ZoneInfo("Europe/London")
SCHEDULE = {"midnight": 0, "5pm": 17}

_scheduler: BackgroundScheduler | None = None
_lock = threading.Lock()


def _update_job():
    """Scheduled job to update creator teams."""
    try:
        logger.info("Scheduled update starting...")
        results = update_all_creator_teams(
            progress_callback=lambda m: logger.info("%s", m)
        )
        if not results["already_up_to_date"]:
            logger.info(
                "Update complete: %s/%s successful, %s failed",
                results["success"],
                results["total"],
                results["failed"],
            )
    except Exception:
        logger.exception("Scheduled update failed")


def start_scheduler() -> bool:
    """Start the background scheduler."""
    global _scheduler

    with _lock:
        if is_scheduler_running():
            return True
        try:
            _scheduler = BackgroundScheduler(timezone=UK_TZ)
            for job_id, hour in SCHEDULE.items():
                _scheduler.add_job(
                    _update_job,
                    CronTrigger(hour=hour, minute=0, timezone=UK_TZ),
                    id=job_id,
                )
            _scheduler.start()
            logger.info("Scheduler started: updates at midnight and 5pm UK time")
            return True
        except Exception:
            logger.exception("Failed to start scheduler")
            _scheduler = None
            return False


def is_scheduler_running() -> bool:
    """Check if scheduler is running."""
    return _scheduler is not None and _scheduler.running
