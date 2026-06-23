"""Leader election via a Postgres lease table. One atomic conditional UPDATE
decides who holds the lease each tick -- Postgres's own row-level locking
serializes concurrent attempts, so exactly one instance can ever win a given
acquisition, with no separate locking primitive needed.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import case, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from backend.shared.models import Scheduler, SchedulerElection, SchedulerLeadership

LOCK_NAME = "scheduler"


def register_scheduler(db: Session, scheduler_name: str) -> None:
    now = datetime.now(timezone.utc)
    stmt = (
        pg_insert(Scheduler)
        .values(
            scheduler_name=scheduler_name,
            is_leader=False,
            failed_election_attempts=0,
            started_at=now,
            last_seen_at=now,
        )
        .on_conflict_do_update(
            index_elements=[Scheduler.scheduler_name],
            # Re-registering clears any prior archival, same contract as
            # worker registration -- booting up is proof it isn't gone.
            set_={"started_at": now, "last_seen_at": now, "updated_at": now, "archived_at": None},
        )
    )
    db.execute(stmt)
    db.commit()


@dataclass
class ElectionResult:
    became_leader: bool
    term: int
    # True only when the lease looked free/expired at read time but this
    # instance's UPDATE still matched 0 rows -- a genuine lost race, not
    # the routine steady-state of "someone else is healthily leading".
    contended: bool


def attempt_leadership(db: Session, scheduler_id: str, lease_seconds: float) -> ElectionResult:
    db_now = db.execute(select(func.now())).scalar_one()

    current = db.execute(
        select(SchedulerLeadership.leader_id, SchedulerLeadership.lease_expires_at, SchedulerLeadership.term).where(
            SchedulerLeadership.lock_name == LOCK_NAME
        )
    ).one()
    looked_acquirable = (
        current.leader_id is None
        or current.leader_id == scheduler_id
        or current.lease_expires_at is None
        or current.lease_expires_at < db_now
    )

    is_new_leader = or_(SchedulerLeadership.leader_id.is_(None), SchedulerLeadership.leader_id != scheduler_id)
    new_expiry = db_now + timedelta(seconds=lease_seconds)

    row = db.execute(
        update(SchedulerLeadership)
        .where(
            SchedulerLeadership.lock_name == LOCK_NAME,
            or_(
                SchedulerLeadership.leader_id == scheduler_id,
                SchedulerLeadership.leader_id.is_(None),
                SchedulerLeadership.lease_expires_at < db_now,
            ),
        )
        .values(
            leader_id=scheduler_id,
            lease_expires_at=new_expiry,
            last_renewed_at=db_now,
            acquired_at=case((is_new_leader, db_now), else_=SchedulerLeadership.acquired_at),
            term=case((is_new_leader, SchedulerLeadership.term + 1), else_=SchedulerLeadership.term),
        )
        .returning(SchedulerLeadership.term)
    ).first()
    db.commit()

    if row is not None:
        return ElectionResult(became_leader=True, term=row[0], contended=False)
    return ElectionResult(became_leader=False, term=current.term, contended=looked_acquirable)


def update_scheduler_state(db: Session, scheduler_name: str, result: ElectionResult) -> None:
    db.execute(
        update(Scheduler)
        .where(Scheduler.scheduler_name == scheduler_name)
        .values(
            is_leader=result.became_leader,
            last_seen_at=func.now(),
            failed_election_attempts=(
                Scheduler.failed_election_attempts + 1 if result.contended else Scheduler.failed_election_attempts
            ),
        )
    )
    db.commit()


def record_election(db: Session, term: int, leader_id: str) -> None:
    db.add(SchedulerElection(term=term, leader_id=leader_id))
    db.commit()
