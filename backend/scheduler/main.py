import logging
import socket
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from backend.scheduler.election import (
    attempt_leadership,
    record_election,
    register_scheduler,
    update_scheduler_state,
)
from backend.shared.config import settings
from backend.shared.db import SessionLocal
from backend.shared.enums import ExecutionStatus, JobStatus
from backend.shared.models import Job, JobExecution
from backend.shared.queue import enqueue_execution
from backend.shared.redis_client import get_redis_client
from backend.shared.scheduling import compute_next_run_after_execution

logging.basicConfig(level=logging.INFO, format="%(asctime)s scheduler %(levelname)s %(message)s")
logger = logging.getLogger("scheduler")

# Hostname alone, same idiom as worker identity (Phase 2): unique and stable
# per container for its whole lifetime.
SCHEDULER_ID = socket.gethostname()


def run_once(db: Session, redis_client) -> int:
    now = datetime.now(timezone.utc)
    due_jobs = list(
        db.execute(
            select(Job).where(
                Job.status == JobStatus.ACTIVE, Job.deleted_at.is_(None), Job.next_run_at <= now
            )
        )
        .scalars()
        .all()
    )

    scheduled = 0
    for job in due_jobs:
        next_run = compute_next_run_after_execution(job.schedule_type, job.schedule_config, now)
        new_status = JobStatus.COMPLETED if next_run is None else JobStatus.ACTIVE
        new_next_run_at = job.next_run_at if next_run is None else next_run

        # Conditional claim: only proceed if next_run_at still matches what
        # was just read. This, not lease timing, is what actually prevents
        # duplicate scheduling -- even in a brief window where two scheduler
        # instances both believe they're leader, at most one of them can win
        # this UPDATE for a given firing. Same idempotency-guard pattern as
        # the worker's conditional terminal-write from Phase 3.
        claimed = db.execute(
            update(Job)
            .where(Job.id == job.id, Job.next_run_at == job.next_run_at)
            .values(next_run_at=new_next_run_at, status=new_status)
        ).rowcount
        db.commit()

        if not claimed:
            continue

        execution_id = uuid.uuid4()
        db.add(
            JobExecution(
                id=execution_id,
                job_id=job.id,
                status=ExecutionStatus.QUEUED,
                attempt_number=1,
                max_attempts=settings.default_max_attempts,
                root_execution_id=execution_id,
            )
        )
        db.commit()

        enqueue_execution(redis_client, execution_id, job.id)
        logger.info("enqueued execution %s for job %s (%s)", execution_id, job.id, job.name)
        scheduled += 1

    return scheduled


def main() -> None:
    redis_client = get_redis_client()

    db = SessionLocal()
    try:
        register_scheduler(db, SCHEDULER_ID)
    finally:
        db.close()

    logger.info("scheduler %s started, polling every %ss", SCHEDULER_ID, settings.scheduler_poll_interval_seconds)
    was_leader = False
    while True:
        db = SessionLocal()
        try:
            result = attempt_leadership(db, SCHEDULER_ID, settings.leader_lease_seconds)
            update_scheduler_state(db, SCHEDULER_ID, result)

            if result.became_leader and not was_leader:
                logger.info("scheduler %s became LEADER (term %d)", SCHEDULER_ID, result.term)
                record_election(db, result.term, SCHEDULER_ID)
            elif not result.became_leader and was_leader:
                logger.info("scheduler %s lost leadership", SCHEDULER_ID)
            was_leader = result.became_leader

            if result.became_leader:
                count = run_once(db, redis_client)
                if count:
                    logger.info("processed %d due job(s)", count)
        except Exception:
            logger.exception("scheduler tick failed")
            db.rollback()
        finally:
            db.close()
        time.sleep(settings.scheduler_poll_interval_seconds)


if __name__ == "__main__":
    main()
