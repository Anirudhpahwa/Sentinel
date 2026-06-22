import redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.metrics.schemas import QueueMetrics
from backend.metrics.window import recent_cutoff
from backend.shared.config import settings
from backend.shared.enums import ExecutionStatus
from backend.shared.models import JobExecution


def compute_queue_metrics(db: Session, redis_client: redis.Redis) -> QueueMetrics:
    # The real queue depth comes from Redis (LLEN), not from counting QUEUED
    # rows in Postgres -- these can diverge (e.g. a row commits as QUEUED
    # but the scheduler's Redis push then fails), and Redis is the thing
    # workers actually consume from.
    queue_depth = redis_client.llen(settings.job_queue_key)

    oldest_queued_at = db.execute(
        select(func.min(JobExecution.queued_at)).where(
            JobExecution.status.in_([ExecutionStatus.QUEUED, ExecutionStatus.REQUEUED])
        )
    ).scalar_one()

    oldest_pending_age_seconds = None
    if oldest_queued_at is not None:
        db_now = db.execute(select(func.now())).scalar_one()
        oldest_pending_age_seconds = round((db_now - oldest_queued_at).total_seconds(), 2)

    cutoff = recent_cutoff(db)
    wait_seconds = func.extract("epoch", JobExecution.started_at - JobExecution.queued_at)
    average_wait_seconds = db.execute(
        select(func.avg(wait_seconds)).where(JobExecution.started_at.is_not(None), JobExecution.started_at >= cutoff)
    ).scalar_one()

    return QueueMetrics(
        queue_depth=queue_depth,
        oldest_pending_age_seconds=oldest_pending_age_seconds,
        average_wait_seconds=round(average_wait_seconds, 2) if average_wait_seconds is not None else None,
    )
