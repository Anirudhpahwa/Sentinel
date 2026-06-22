"""Schedule interpretation: the only place that maps a job's
(schedule_type, schedule_config) onto a concrete point in time.

Used by the API at job-creation time (compute_initial_next_run) and by the
scheduler after each run (compute_next_run_after_execution). Adding a new
schedule_type later (e.g. CRON) means adding one branch here -- never a
migration on the jobs table.
"""

from datetime import datetime, timedelta
from typing import Any

from backend.shared.enums import ScheduleType


def compute_initial_next_run(schedule_type: str, schedule_config: dict[str, Any], now: datetime) -> datetime:
    if schedule_type == ScheduleType.ONCE:
        return datetime.fromisoformat(schedule_config["run_at"])
    if schedule_type == ScheduleType.INTERVAL:
        return now
    raise ValueError(f"Unknown schedule_type: {schedule_type}")


def compute_next_run_after_execution(
    schedule_type: str, schedule_config: dict[str, Any], now: datetime
) -> datetime | None:
    """Returns the next run time, or None if the job should not run again."""
    if schedule_type == ScheduleType.ONCE:
        return None
    if schedule_type == ScheduleType.INTERVAL:
        return now + timedelta(seconds=schedule_config["interval_seconds"])
    raise ValueError(f"Unknown schedule_type: {schedule_type}")
