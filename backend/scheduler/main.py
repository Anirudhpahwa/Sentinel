import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.shared.config import settings
from backend.shared.db import SessionLocal
from backend.shared.enums import ExecutionStatus, JobStatus
from backend.shared.models import Job, JobExecution
from backend.shared.queue import enqueue_execution
from backend.shared.redis_client import get_redis_client
from backend.shared.scheduling import compute_next_run_after_execution

logging.basicConfig(level=logging.INFO, format="%(asctime)s scheduler %(levelname)s %(message)s")
logger = logging.getLogger("scheduler")


def run_once(db: Session, redis_client) -> int:
    now = datetime.now(timezone.utc)
    due_jobs = list(
        db.execute(select(Job).where(Job.status == JobStatus.ACTIVE, Job.next_run_at <= now)).scalars().all()
    )

    for job in due_jobs:
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

        next_run = compute_next_run_after_execution(job.schedule_type, job.schedule_config, now)
        if next_run is None:
            job.status = JobStatus.COMPLETED
        else:
            job.next_run_at = next_run

        # Commit per job (not batched) so one job's failure can't block others,
        # and so the Redis push below only happens once the DB state is durable.
        db.commit()

        enqueue_execution(redis_client, execution_id, job.id)
        logger.info("enqueued execution %s for job %s (%s)", execution_id, job.id, job.name)

    return len(due_jobs)


def main() -> None:
    redis_client = get_redis_client()
    logger.info("scheduler started, polling every %ss", settings.scheduler_poll_interval_seconds)
    while True:
        db = SessionLocal()
        try:
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
