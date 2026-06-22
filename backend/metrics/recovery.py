from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.metrics.schemas import RecoveryMetrics
from backend.metrics.window import recent_cutoff
from backend.shared.enums import ExecutionStatus
from backend.shared.models import JobExecution


def compute_recovery_metrics(db: Session) -> RecoveryMetrics:
    cutoff = recent_cutoff(db)

    # "Attempts" = every row the recovery service actually intervened on
    # (it always sets abandoned_reason), regardless of whether that led to a
    # retry or to giving up -- distinct from "Requeued", which counts only
    # the fresh retry rows that were actually spawned.
    attempts = db.execute(
        select(func.count())
        .select_from(JobExecution)
        .where(JobExecution.abandoned_reason.is_not(None), JobExecution.updated_at >= cutoff)
    ).scalar_one()

    abandoned = db.execute(
        select(func.count())
        .select_from(JobExecution)
        .where(JobExecution.status == ExecutionStatus.ABANDONED, JobExecution.updated_at >= cutoff)
    ).scalar_one()

    retries = select(func.count()).select_from(JobExecution).where(
        JobExecution.queued_at >= cutoff, JobExecution.attempt_number > 1
    )
    requeued = db.execute(retries).scalar_one()
    retry_successes = db.execute(retries.where(JobExecution.status == ExecutionStatus.SUCCEEDED)).scalar_one()
    retry_failures = db.execute(
        retries.where(
            JobExecution.status.in_(
                [ExecutionStatus.FAILED, ExecutionStatus.ABANDONED, ExecutionStatus.PERMANENTLY_FAILED]
            )
        )
    ).scalar_one()
    retry_terminal_failures = db.execute(
        retries.where(JobExecution.status.in_([ExecutionStatus.FAILED, ExecutionStatus.PERMANENTLY_FAILED]))
    ).scalar_one()

    resolved = retry_successes + retry_terminal_failures
    success_rate = (retry_successes / resolved * 100) if resolved else None

    return RecoveryMetrics(
        recovery_attempts_recent=attempts,
        recovery_successes_recent=retry_successes,
        recovery_failures_recent=retry_failures,
        abandoned_executions_recent=abandoned,
        requeued_executions_recent=requeued,
        recovery_success_rate_percent=round(success_rate, 1) if success_rate is not None else None,
    )
