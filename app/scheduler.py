"""Background scheduler for updating creator teams at 5pm and midnight UK time."""

import logging
import threading
from typing import Optional

try:
    import pytz
    from apscheduler.schedulers.background import BackgroundScheduler
    from apscheduler.triggers.cron import CronTrigger
    APSCHEDULER_AVAILABLE = True
except ImportError:
    APSCHEDULER_AVAILABLE = False
    BackgroundScheduler = None
    CronTrigger = None
    pytz = None

from app.update_creator_teams import update_all_creator_teams

logger = logging.getLogger(__name__)
UK_TZ = pytz.timezone("Europe/London") if pytz else None

_scheduler: Optional[BackgroundScheduler] = None
_lock = threading.Lock()


def _update_job():
    """Scheduled job to update creator teams."""
    try:
        logger.info("Scheduled update starting...")
        results = update_all_creator_teams(progress_callback=lambda m: logger.info(m))
        if not results.get("already_up_to_date", False):
            s, f, t = results.get("success", 0), results.get("failed", 0), results.get("total", 0)
            logger.info(f"Update complete: {s}/{t} successful, {f} failed")
    except Exception as e:
        logger.error(f"Scheduled update failed: {e}", exc_info=True)


def start_scheduler():
    """Start the background scheduler."""
    global _scheduler
    
    if not APSCHEDULER_AVAILABLE:
        logger.warning("APScheduler not available")
        return False
    
    with _lock:
        if _scheduler is not None and _scheduler.running:
            return True
        
        try:
            _scheduler = BackgroundScheduler(timezone=UK_TZ)
            _scheduler.add_job(_update_job, CronTrigger(hour=0, minute=0, timezone=UK_TZ), id="midnight")
            _scheduler.add_job(_update_job, CronTrigger(hour=17, minute=0, timezone=UK_TZ), id="5pm")
            _scheduler.start()
            logger.info("Scheduler started: updates at midnight and 5pm UK time")
            return True
        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}", exc_info=True)
            _scheduler = None
            return False


def is_scheduler_running() -> bool:
    """Check if scheduler is running."""
    return _scheduler is not None and _scheduler.running

