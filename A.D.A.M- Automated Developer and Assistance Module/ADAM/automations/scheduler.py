"""Scheduler: manage cron, interval, and one-time schedules."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


class Schedule:
    """Parsed schedule definition."""

    def __init__(self, schedule_type: str, raw: str, tz: str = "UTC"):
        self.schedule_type = schedule_type
        self.raw = raw
        self.tz = tz

    def next_run(self, now: Optional[datetime] = None) -> Optional[datetime]:
        """Return the next scheduled run time."""
        raise NotImplementedError


class CronSchedule(Schedule):
    def __init__(self, cron_expr: str, tz: str = "UTC"):
        super().__init__("cron", cron_expr, tz)
        self.cron_expr = cron_expr

    def next_run(self, now: Optional[datetime] = None) -> Optional[datetime]:
        now = now or datetime.utcnow()
        try:
            from croniter import croniter
            return croniter(self.cron_expr, now).get_next(datetime)
        except Exception:
            return None


class IntervalSchedule(Schedule):
    def __init__(self, seconds: int, tz: str = "UTC"):
        super().__init__("interval", f"every {seconds} seconds", tz)
        self.seconds = seconds

    def next_run(self, now: Optional[datetime] = None) -> Optional[datetime]:
        now = now or datetime.utcnow()
        return now + __import__("datetime").timedelta(seconds=self.seconds)


class OneTimeSchedule(Schedule):
    def __init__(self, run_at: str, tz: str = "UTC"):
        super().__init__("onetime", run_at, tz)
        self.run_at = run_at

    def next_run(self, now: Optional[datetime] = None) -> Optional[datetime]:
        try:
            return datetime.fromisoformat(self.run_at)
        except ValueError:
            return None


def parse_schedule(raw: str) -> Schedule:
    raw = raw.strip()
    if raw.lower().startswith("every "):
        return _parse_interval(raw)
    if raw.lower() == "run once":
        return OneTimeSchedule(run_at=datetime.utcnow().isoformat())
    if " " in raw:
        parts = raw.split()
        if len(parts) in (5, 6):
            return CronSchedule(cron_expr=raw)
        raise ValueError(f"Unsupported schedule format: {raw}")
    raise ValueError(f"Unsupported schedule format: {raw}")


def _parse_interval(raw: str) -> IntervalSchedule:
    parts = raw.lower().split()
    if len(parts) < 3:
        raise ValueError(f"Unsupported interval format: {raw}")
    value_str = parts[1]
    unit = parts[2]
    if not value_str.isdigit():
        raise ValueError(f"Unsupported interval format: {raw}")
    value = int(value_str)
    multipliers = {
        "s": 1,
        "sec": 1,
        "seconds": 1,
        "m": 60,
        "min": 60,
        "minutes": 60,
        "h": 3600,
        "hr": 3600,
        "hours": 3600,
    }
    seconds = value * multipliers.get(unit.rstrip("s").rstrip("."), 1)
    return IntervalSchedule(seconds=seconds)
