import logging
import time
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.shared.config import settings
from backend.shared.db import SessionLocal
from backend.shared.enums import ExecutionStatus, LogLevel, WorkerStatus
from backend.shared.logs import write_log
from backend.shared.models import JobExecution, Worker
from backend.shared.queue import enqueue_execution
from backend.shared.redis_client import get_redis_client

logging.basicConfig(level=logging.INFO, format="%(asctime)s recovery %(levelname)s %(message)s")
logger = logging.getLogger("recovery")


def find_orphaned_executions(db: Session) -> list[JobExecution]:
    # Liveness is never re-derived here -- workers.status is the health
    # monitor's pre-computed, server-clock-safe answer to "is this worker
    # alive." Recovery only ever consumes that signal, never produces it.
    return list(
        db.execute(
            select(JobExecution)
            .join(Worker, Worker.worker_name == JobExecution.worker_id)
            .where(JobExecution.status == ExecutionStatus.RUNNING, Worker.status == WorkerStatus.OFFLINE)
        )
        .scalars()
        .all()
    )


def recover_execution(db: Session, redis_client, execution: JobExecution) -> None:
    root_id = execution.root_execution_id or execution.id

    if execution.attempt_number >= execution.max_attempts:
        execution.status = ExecutionStatus.PERMANENTLY_FAILED
        execution.abandoned_reason = (
            f"Worker {execution.worker_id} went OFFLINE; "
            f"retry attempts exhausted ({execution.attempt_number}/{execution.max_attempts})"
        )
        db.commit()
        write_log(
            db,
            execution.id,
            f"Recovery attempts exhausted ({execution.attempt_number}/{execution.max_attempts}); "
            "marking permanently failed",
            level=LogLevel.ERROR,
        )
        logger.info("execution %s permanently failed after %d attempts", execution.id, execution.attempt_number)
        return

    execution.status = ExecutionStatus.ABANDONED
    execution.abandoned_reason = f"Worker {execution.worker_id} went OFFLINE while RUNNING"
    db.commit()
    write_log(
        db, execution.id, f"Execution abandoned: worker {execution.worker_id} is OFFLINE", level=LogLevel.WARNING
    )

    new_execution_id = uuid.uuid4()
    new_attempt = execution.attempt_number + 1
    db.add(
        JobExecution(
            id=new_execution_id,
            job_id=execution.job_id,
            status=ExecutionStatus.REQUEUED,
            attempt_number=new_attempt,
            max_attempts=execution.max_attempts,
            root_execution_id=root_id,
        )
    )
    # Commit before the Redis push, same ordering discipline as the
    # scheduler: a failed push leaves a visible, stuck REQUEUED row rather
    # than risking a duplicate enqueue if the push "succeeded" but the
    # commit hadn't landed.
    db.commit()
    write_log(
        db,
        new_execution_id,
        f"Requeued as attempt {new_attempt} of {execution.max_attempts} (recovering execution {execution.id})",
    )

    enqueue_execution(redis_client, new_execution_id, execution.job_id)
    logger.info(
        "recovered execution %s -> %s (attempt %d/%d)",
        execution.id,
        new_execution_id,
        new_attempt,
        execution.max_attempts,
    )


def run_once(db: Session, redis_client) -> int:
    orphans = find_orphaned_executions(db)
    for execution in orphans:
        recover_execution(db, redis_client, execution)
    return len(orphans)


def main() -> None:
    redis_client = get_redis_client()
    logger.info("recovery service started, polling every %ss", settings.recovery_check_interval_seconds)
    while True:
        db = SessionLocal()
        try:
            count = run_once(db, redis_client)
            if count:
                logger.info("recovered %d orphaned execution(s)", count)
        except Exception:
            logger.exception("recovery tick failed")
            db.rollback()
        finally:
            db.close()
        time.sleep(settings.recovery_check_interval_seconds)


if __name__ == "__main__":
    main()
