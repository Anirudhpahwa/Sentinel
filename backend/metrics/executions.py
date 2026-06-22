from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.metrics.schemas import ExecutionMetrics
from backend.metrics.window import recent_cutoff
from backend.shared.enums import ExecutionStatus
from backend.shared.models import JobExecution


def compute_execution_metrics(db: Session) -> ExecutionMetrics:
    cutoff = recent_cutoff(db)
    hour_cutoff = recent_cutoff(db, hours=1)

    executions_recent = db.execute(
        select(func.count()).select_from(JobExecution).where(JobExecution.queued_at >= cutoff)
    ).scalar_one()

    executions_last_hour = db.execute(
        select(func.count()).select_from(JobExecution).where(JobExecution.queued_at >= hour_cutoff)
    ).scalar_one()

    successful_recent = db.execute(
        select(func.count())
        .select_from(JobExecution)
        .where(JobExecution.queued_at >= cutoff, JobExecution.status == ExecutionStatus.SUCCEEDED)
    ).scalar_one()

    failed_recent = db.execute(
        select(func.count())
        .select_from(JobExecution)
        .where(
            JobExecution.queued_at >= cutoff,
            JobExecution.status.in_([ExecutionStatus.FAILED, ExecutionStatus.PERMANENTLY_FAILED]),
        )
    ).scalar_one()

    # percentile_cont runs server-side over an indexed, window-bounded set --
    # never pulls raw durations into Python, never scans the full history.
    duration_seconds = func.extract("epoch", JobExecution.completed_at - JobExecution.started_at)
    average_duration, p95_duration = db.execute(
        select(func.avg(duration_seconds), func.percentile_cont(0.95).within_group(duration_seconds)).where(
            JobExecution.completed_at.is_not(None),
            JobExecution.started_at.is_not(None),
            JobExecution.completed_at >= cutoff,
        )
    ).one()

    current_running = db.execute(
        select(func.count()).select_from(JobExecution).where(JobExecution.status == ExecutionStatus.RUNNING)
    ).scalar_one()

    return ExecutionMetrics(
        executions_recent=executions_recent,
        executions_last_hour=executions_last_hour,
        successful_executions_recent=successful_recent,
        failed_executions_recent=failed_recent,
        average_duration_seconds=round(average_duration, 2) if average_duration is not None else None,
        p95_duration_seconds=round(p95_duration, 2) if p95_duration is not None else None,
        current_running=current_running,
    )
