from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.metrics.schemas import SchedulerMetrics
from backend.metrics.window import recent_cutoff
from backend.shared.config import settings
from backend.shared.models import Scheduler, SchedulerElection, SchedulerLeadership

STALE_AFTER_SECONDS = settings.leader_lease_seconds * 3


def compute_scheduler_metrics(db: Session) -> SchedulerMetrics:
    db_now = db.execute(select(func.now())).scalar_one()

    leadership = db.execute(
        select(SchedulerLeadership).where(SchedulerLeadership.lock_name == "scheduler")
    ).scalar_one()
    lease_valid = leadership.lease_expires_at is not None and leadership.lease_expires_at >= db_now

    current_leader = leadership.leader_id if lease_valid else None
    leader_since = leadership.acquired_at if lease_valid else None
    leader_uptime_seconds = (db_now - leader_since).total_seconds() if leader_since else None

    active_schedulers = db.execute(
        select(func.count())
        .select_from(Scheduler)
        .where(func.extract("epoch", db_now - Scheduler.last_seen_at) <= STALE_AFTER_SECONDS)
    ).scalar_one()

    leader_elections_total = db.execute(select(func.count()).select_from(SchedulerElection)).scalar_one()

    cutoff = recent_cutoff(db)
    leadership_changes_recent = db.execute(
        select(func.count()).select_from(SchedulerElection).where(SchedulerElection.elected_at >= cutoff)
    ).scalar_one()

    failed_election_attempts_total = db.execute(select(func.sum(Scheduler.failed_election_attempts))).scalar_one()

    return SchedulerMetrics(
        current_leader=current_leader,
        leader_since=leader_since,
        leader_uptime_seconds=round(leader_uptime_seconds, 1) if leader_uptime_seconds is not None else None,
        active_schedulers=active_schedulers,
        leader_elections_total=leader_elections_total,
        leadership_changes_recent=leadership_changes_recent,
        failed_election_attempts_total=failed_election_attempts_total or 0,
    )
