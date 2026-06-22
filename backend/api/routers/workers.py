import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.shared.enums import ExecutionStatus
from backend.shared.models import JobExecution, Worker
from backend.shared.schemas import WorkerRead

router = APIRouter(prefix="/workers", tags=["workers"])


def _execution_counts(db: Session, worker_name: str | None = None) -> dict[str, dict[str, int]]:
    query = select(JobExecution.worker_id, JobExecution.status, func.count()).where(
        JobExecution.worker_id.is_not(None)
    )
    if worker_name is not None:
        query = query.where(JobExecution.worker_id == worker_name)
    query = query.group_by(JobExecution.worker_id, JobExecution.status)

    counts: dict[str, dict[str, int]] = {}
    for name, status, count in db.execute(query).all():
        counts.setdefault(name, {})[status] = count
    return counts


def _to_worker_read(worker: Worker, counts: dict[str, int]) -> WorkerRead:
    return WorkerRead(
        id=worker.id,
        worker_name=worker.worker_name,
        status=worker.status,
        started_at=worker.started_at,
        last_heartbeat_at=worker.last_heartbeat_at,
        last_seen_at=worker.last_seen_at,
        executions_completed=counts.get(ExecutionStatus.SUCCEEDED, 0),
        executions_failed=counts.get(ExecutionStatus.FAILED, 0),
    )


@router.get("", response_model=list[WorkerRead])
def list_workers(db: Session = Depends(get_db)) -> list[WorkerRead]:
    workers = list(db.execute(select(Worker).order_by(Worker.worker_name)).scalars().all())
    counts = _execution_counts(db)
    return [_to_worker_read(w, counts.get(w.worker_name, {})) for w in workers]


@router.get("/{worker_id}", response_model=WorkerRead)
def get_worker(worker_id: uuid.UUID, db: Session = Depends(get_db)) -> WorkerRead:
    worker = db.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    counts = _execution_counts(db, worker.worker_name)
    return _to_worker_read(worker, counts.get(worker.worker_name, {}))
