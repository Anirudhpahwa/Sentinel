from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.shared.config import settings
from backend.shared.models import Scheduler, SchedulerElection
from backend.shared.schemas import SchedulerElectionRead, SchedulerRead

router = APIRouter(prefix="/schedulers", tags=["schedulers"])

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
        started_at=scheduler.started_at,
        last_seen_at=scheduler.last_seen_at,
        failed_election_attempts=scheduler.failed_election_attempts,
    )


@router.get("", response_model=list[SchedulerRead])
def list_schedulers(db: Session = Depends(get_db)) -> list[SchedulerRead]:
    db_now = db.execute(select(func.now())).scalar_one()
    schedulers = list(db.execute(select(Scheduler).order_by(Scheduler.scheduler_name)).scalars().all())
    return [_to_scheduler_read(s, db_now) for s in schedulers]


@router.get("/elections", response_model=list[SchedulerElectionRead])
def list_elections(
    limit: int = Query(default=20, ge=1, le=200), db: Session = Depends(get_db)
) -> list[SchedulerElection]:
    return list(
        db.execute(select(SchedulerElection).order_by(SchedulerElection.elected_at.desc()).limit(limit))
        .scalars()
        .all()
    )
