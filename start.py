"""
Entry point for Railway. Runs Streamlit during the day (7am–10pm UK) and the
offline HTTP server at night (10pm–7am UK), restarting itself at each boundary.
"""

import os
import subprocess
import sys
import time
from datetime import datetime, timedelta

import pytz

UK_TZ = pytz.timezone("Europe/London")
OFF_START = 22  # 10pm
OFF_END = 7     # 7am


def _seconds_until(target_hour: int) -> float:
    now = datetime.now(UK_TZ)
    target = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    return (target - now).total_seconds()


def _is_off_hours() -> bool:
    h = datetime.now(UK_TZ).hour
    return h >= OFF_START or h < OFF_END


port = os.environ.get("PORT", "8501")

if _is_off_hours():
    secs = _seconds_until(OFF_END)
    print(f"Off-hours. Running offline server for {secs/3600:.1f}h until 7am UK time.", flush=True)
    proc = subprocess.Popen([sys.executable, "offline.py"])
else:
    secs = _seconds_until(OFF_START)
    print(f"On-hours. Running Streamlit for {secs/3600:.1f}h until 10pm UK time.", flush=True)
    proc = subprocess.Popen([
        "streamlit", "run", "app.py",
        "--server.port", port,
        "--server.address", "0.0.0.0",
    ])

try:
    time.sleep(secs)
finally:
    proc.terminate()
    proc.wait()

# Non-zero exit triggers Railway's restart policy, which re-enters this script.
sys.exit(1)
