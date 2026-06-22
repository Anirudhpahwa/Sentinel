from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.metrics.schemas import TrendBucket, TrendsResponse
from backend.shared.enums import ExecutionStatus
from backend.shared.models import JobExecution


def compute_trends(db: Session, hours: int) -> TrendsResponse:
    db_now = db.execute(select(func.now())).scalar_one()
    since = db_now - timedelta(hours=hours)

    bucket = func.date_trunc("hour", JobExecution.queued_at)
    rows = db.execute(
        select(
            bucket.label("bucket_start"),
            func.count().label("executions"),
            func.count()
            .filter(JobExecution.status.in_([ExecutionStatus.FAILED, ExecutionStatus.PERMANENTLY_FAILED]))
            .label("failures"),
            func.count().filter(JobExecution.attempt_number > 1).label("recoveries"),
        )
        .where(JobExecution.queued_at >= since)
        .group_by(bucket)
    ).all()
    by_bucket = {row.bucket_start: row for row in rows}

    # Fill every hour in the window, including zero-activity ones, so the
    # chart shows a continuous timeline instead of gaps where nothing ran.
    buckets: list[TrendBucket] = []
    cursor = since.replace(minute=0, second=0, microsecond=0)
    end = db_now.replace(minute=0, second=0, microsecond=0)
    while cursor <= end:
        row = by_bucket.get(cursor)
        buckets.append(
            TrendBucket(
                bucket_start=cursor,
                executions=row.executions if row else 0,
                failures=row.failures if row else 0,
                recoveries=row.recoveries if row else 0,
            )
        )
        cursor += timedelta(hours=1)

    return TrendsResponse(window_hours=hours, buckets=buckets)
