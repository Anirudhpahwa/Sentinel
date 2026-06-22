import redis
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.metrics.executions import compute_execution_metrics
from backend.metrics.queue import compute_queue_metrics
from backend.metrics.recovery import compute_recovery_metrics
from backend.metrics.schemas import OverviewMetrics
from backend.metrics.workers import compute_worker_metrics
from backend.shared.enums import JobStatus
from backend.shared.models import Job


def compute_overview(db: Session, redis_client: redis.Redis) -> OverviewMetrics:
    active_jobs = db.execute(
        select(func.count()).select_from(Job).where(Job.status == JobStatus.ACTIVE)
    ).scalar_one()

    worker_metrics = compute_worker_metrics(db)
    execution_metrics = compute_execution_metrics(db)
    queue_metrics = compute_queue_metrics(db, redis_client)
    recovery_metrics = compute_recovery_metrics(db)

    resolved = execution_metrics.successful_executions_recent + execution_metrics.failed_executions_recent
    success_rate = execution_metrics.successful_executions_recent / resolved * 100 if resolved else None

    return OverviewMetrics(
        active_jobs=active_jobs,
        healthy_workers=worker_metrics.healthy_workers,
        queue_depth=queue_metrics.queue_depth,
        executions_recent=execution_metrics.executions_recent,
        success_rate_percent=round(success_rate, 1) if success_rate is not None else None,
        recovery_count_recent=recovery_metrics.recovery_attempts_recent,
    )
