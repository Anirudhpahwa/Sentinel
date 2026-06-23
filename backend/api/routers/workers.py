import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.shared.audit import record_admin_action
from backend.shared.enums import ExecutionStatus, WorkerStatus
from backend.shared.models import JobExecution, Worker
from backend.shared.schemas import WorkerRead

router = APIRouter(prefix="/workers", tags=["workers"])

WorkerView = Literal["active", "offline", "archived"]


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
        worker_serial=worker.worker_serial,
        status=worker.status,
        is_archived=worker.archived_at is not None,
        started_at=worker.started_at,
        last_heartbeat_at=worker.last_heartbeat_at,
        last_seen_at=worker.last_seen_at,
        executions_completed=counts.get(ExecutionStatus.SUCCEEDED, 0),
        executions_failed=counts.get(ExecutionStatus.FAILED, 0),
    )


@router.get("", response_model=list[WorkerRead])
def list_workers(view: WorkerView = Query(default="active"), db: Session = Depends(get_db)) -> list[WorkerRead]:
    query = select(Worker)
    if view == "archived":
        query = query.where(Worker.archived_at.is_not(None))
    elif view == "offline":
        query = query.where(Worker.archived_at.is_(None), Worker.status == WorkerStatus.OFFLINE)
    else:
        query = query.where(Worker.archived_at.is_(None), Worker.status != WorkerStatus.OFFLINE)

    workers = list(
        db.execute(
            query.order_by(Worker.worker_serial.is_(None), Worker.worker_serial, Worker.worker_name)
        )
        .scalars()
        .all()
    )
    counts = _execution_counts(db)
    return [_to_worker_read(w, counts.get(w.worker_name, {})) for w in workers]


@router.get("/{worker_id}", response_model=WorkerRead)
def get_worker(worker_id: uuid.UUID, db: Session = Depends(get_db)) -> WorkerRead:
    worker = db.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    counts = _execution_counts(db, worker.worker_name)
    return _to_worker_read(worker, counts.get(worker.worker_name, {}))


@router.post("/{worker_id}/archive", response_model=WorkerRead)
def archive_worker(worker_id: uuid.UUID, db: Session = Depends(get_db)) -> WorkerRead:
    worker = db.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    if worker.archived_at is None:
        worker.archived_at = datetime.now(timezone.utc)
        db.commit()
        record_admin_action(
            db, action="ARCHIVE_WORKER", target_type="worker", target_id=str(worker_id), detail=worker.worker_name
        )
    counts = _execution_counts(db, worker.worker_name)
    return _to_worker_read(worker, counts.get(worker.worker_name, {}))


@router.post("/{worker_id}/restore", response_model=WorkerRead)
def restore_worker(worker_id: uuid.UUID, db: Session = Depends(get_db)) -> WorkerRead:
    worker = db.get(Worker, worker_id)
    if worker is None:
        raise HTTPException(status_code=404, detail="Worker not found")
    if worker.archived_at is not None:
        worker.archived_at = None
        db.commit()
        record_admin_action(
            db, action="RESTORE_WORKER", target_type="worker", target_id=str(worker_id), detail=worker.worker_name
        )
    counts = _execution_counts(db, worker.worker_name)
    return _to_worker_read(worker, counts.get(worker.worker_name, {}))
