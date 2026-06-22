from sqlalchemy import distinct, func, select
from sqlalchemy.orm import Session

from backend.metrics.schemas import WorkerMetrics
from backend.metrics.window import recent_cutoff
from backend.shared.enums import ExecutionStatus, WorkerStatus
from backend.shared.models import JobExecution, Worker


def compute_worker_metrics(db: Session) -> WorkerMetrics:
    # Scoped to the rolling window by last_heartbeat_at so workers from
    # long-destroyed containers (which sit OFFLINE forever, by design since
    # Phase 2) don't make "Total Workers" grow without bound -- this counts
    # the current fleet, not the full historical registry.
    cutoff = recent_cutoff(db)
    rows = db.execute(
        select(Worker.status, func.count()).where(Worker.last_heartbeat_at >= cutoff).group_by(Worker.status)
    ).all()
    counts = {status: count for status, count in rows}

    healthy = counts.get(WorkerStatus.HEALTHY, 0)
    unhealthy = counts.get(WorkerStatus.UNHEALTHY, 0)
    offline = counts.get(WorkerStatus.OFFLINE, 0)

    busy_workers = db.execute(
        select(func.count(distinct(JobExecution.worker_id))).where(JobExecution.status == ExecutionStatus.RUNNING)
    ).scalar_one()

    available = healthy + unhealthy
    utilization = (busy_workers / available * 100) if available else 0.0

    return WorkerMetrics(
        total_workers=healthy + unhealthy + offline,
        healthy_workers=healthy,
        unhealthy_workers=unhealthy,
        offline_workers=offline,
        utilization_percent=round(utilization, 1),
    )
