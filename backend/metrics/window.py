from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.shared.config import settings


def recent_cutoff(db: Session, hours: int | None = None) -> datetime:
    """'Hours ago', computed from the database's own clock rather than this
    process's local clock, so window boundaries are never skewed by clock
    drift between containers -- same discipline as the scheduler and health
    monitor use for their own time comparisons.
    """
    db_now = db.execute(select(func.now())).scalar_one()
    return db_now - timedelta(hours=hours if hours is not None else settings.metrics_window_hours)
