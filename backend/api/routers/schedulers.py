import uuid
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.shared.audit import record_admin_action
from backend.shared.config import settings
from backend.shared.models import Scheduler, SchedulerElection
from backend.shared.schemas import SchedulerElectionRead, SchedulerRead

router = APIRouter(prefix="/schedulers", tags=["schedulers"])

SchedulerView = Literal["active", "offline", "archived"]

# A scheduler is considered ACTIVE if it has heartbeated within 3 lease
# durations -- generous enough to avoid false positives from a single
# missed tick, while still flagging an instance that's genuinely gone.
STALE_AFTER_SECONDS = settings.leader_lease_seconds * 3


def _to_scheduler_read(scheduler: Scheduler, db_now) -> SchedulerRead:
    age = (db_now - scheduler.last_seen_at).total_seconds()
    return SchedulerRead(
        id=scheduler.id,
        scheduler_name=scheduler.scheduler_name,
        role="LEADER" if scheduler.is_leader else "FOLLOWER",
        status="ACTIVE" if age <= STALE_AFTER_SECONDS else "STALE",
        is_archived=scheduler.archived_at is not None,
        started_at=scheduler.started_at,
        last_seen_at=scheduler.last_seen_at,
        failed_election_attempts=scheduler.failed_election_attempts,
    )


@router.get("", response_model=list[SchedulerRead])
def list_schedulers(view: SchedulerView = Query(default="active"), db: Session = Depends(get_db)) -> list[SchedulerRead]:
    db_now = db.execute(select(func.now())).scalar_one()

    query = select(Scheduler)
    if view == "archived":
        query = query.where(Scheduler.archived_at.is_not(None))
    else:
        query = query.where(Scheduler.archived_at.is_(None))
    schedulers = [_to_scheduler_read(s, db_now) for s in db.execute(query).scalars().all()]

    if view == "active":
        return [s for s in schedulers if s.status == "ACTIVE"]
    if view == "offline":
        return [s for s in schedulers if s.status == "STALE"]
    return schedulers


@router.get("/elections", response_model=list[SchedulerElectionRead])
def list_elections(
    limit: int = Query(default=20, ge=1, le=200), db: Session = Depends(get_db)
) -> list[SchedulerElection]:
    return list(
        db.execute(select(SchedulerElection).order_by(SchedulerElection.elected_at.desc()).limit(limit))
        .scalars()
        .all()
    )


@router.post("/{scheduler_id}/archive", response_model=SchedulerRead)
def archive_scheduler(scheduler_id: uuid.UUID, db: Session = Depends(get_db)) -> SchedulerRead:
    scheduler = db.get(Scheduler, scheduler_id)
    if scheduler is None:
        raise HTTPException(status_code=404, detail="Scheduler not found")
    if scheduler.archived_at is None:
        scheduler.archived_at = datetime.now(timezone.utc)
        db.commit()
        record_admin_action(
            db,
            action="ARCHIVE_SCHEDULER",
            target_type="scheduler",
            target_id=str(scheduler_id),
            detail=scheduler.scheduler_name,
        )
    db_now = db.execute(select(func.now())).scalar_one()
    return _to_scheduler_read(scheduler, db_now)


@router.post("/{scheduler_id}/restore", response_model=SchedulerRead)
def restore_scheduler(scheduler_id: uuid.UUID, db: Session = Depends(get_db)) -> SchedulerRead:
    scheduler = db.get(Scheduler, scheduler_id)
    if scheduler is None:
        raise HTTPException(status_code=404, detail="Scheduler not found")
    if scheduler.archived_at is not None:
        scheduler.archived_at = None
        db.commit()
        record_admin_action(
            db,
            action="RESTORE_SCHEDULER",
            target_type="scheduler",
            target_id=str(scheduler_id),
            detail=scheduler.scheduler_name,
        )
    db_now = db.execute(select(func.now())).scalar_one()
    return _to_scheduler_read(scheduler, db_now)
