import logging
import os
import socket
import threading
import uuid
from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.orm import Session

from backend.shared.config import settings
from backend.shared.db import SessionLocal
from backend.shared.enums import ExecutionStatus, LogLevel
from backend.shared.logs import write_log
from backend.shared.models import Job, JobExecution
from backend.shared.queue import dequeue_execution
from backend.shared.redis_client import get_redis_client
from backend.worker.job_simulators import simulate_job
from backend.worker.registry import register_worker, send_heartbeat, touch_last_seen

logging.basicConfig(level=logging.INFO, format="%(asctime)s worker %(levelname)s %(message)s")
logger = logging.getLogger("worker")

# Hostname alone, not hostname+pid: Docker gives every container a unique,
# stable hostname for its whole lifetime, so this is already collision-free
# across replicas and stable if the process restarts in place.
WORKER_ID = socket.gethostname()

# Set explicitly per service in docker-compose (deploy.replicas can't give
# replicas distinct env vars outside Swarm) -- purely a human-friendly
# terminal reference, never used as the real identity key.
WORKER_SERIAL = int(os.environ["WORKER_SERIAL"]) if os.environ.get("WORKER_SERIAL") else None


def write_terminal_status(
    db: Session, execution_id: uuid.UUID, status: str, result: dict, completed_at: datetime
) -> bool:
    """Conditional write: only succeeds if the row is still RUNNING. Returns
    False if the recovery service already reassigned this execution (e.g. a
    worker that was merely network-partitioned, not actually dead, finishing
    late after recovery moved on) -- a lock-free guard against a stale write
    clobbering state, not a prevention of the underlying duplicate work.
    """
    result_proxy = db.execute(
        update(JobExecution)
        .where(JobExecution.id == execution_id, JobExecution.status == ExecutionStatus.RUNNING)
        .values(status=status, completed_at=completed_at, result=result)
    )
    db.commit()
    return result_proxy.rowcount > 0


def process_execution(db: Session, execution_id: uuid.UUID) -> None:
    execution = db.get(JobExecution, execution_id)
    if execution is None:
        logger.error("execution %s not found, dropping", execution_id)
        return

    job = db.get(Job, execution.job_id)

    execution.status = ExecutionStatus.RUNNING
    execution.started_at = datetime.now(timezone.utc)
    execution.worker_id = WORKER_ID
    db.commit()
    touch_last_seen(db, WORKER_ID)

    if execution.attempt_number > 1:
        write_log(
            db,
            execution.id,
            f"Starting execution (attempt {execution.attempt_number} of {execution.max_attempts}, "
            f"recovering execution {execution.root_execution_id})",
        )
    else:
        write_log(db, execution.id, "Starting execution")
    write_log(db, execution.id, "Loading configuration")

    result, succeeded = simulate_job(job.job_type, job.payload, lambda msg: write_log(db, execution.id, msg))

    final_status = ExecutionStatus.SUCCEEDED if succeeded else ExecutionStatus.FAILED
    completed_at = datetime.now(timezone.utc)
    applied = write_terminal_status(db, execution.id, final_status, result, completed_at)

    if not applied:
        logger.warning("execution %s was reassigned during processing; discarding stale result", execution.id)
        write_log(
            db,
            execution.id,
            "Discarding result: this execution was reassigned to a new attempt while still being processed",
            level=LogLevel.WARNING,
        )
        return

    touch_last_seen(db, WORKER_ID)
    write_log(
        db,
        execution.id,
        "Execution completed" if succeeded else "Execution failed",
        level=LogLevel.INFO if succeeded else LogLevel.ERROR,
    )

    logger.info("execution %s (%s) finished: %s", execution.id, job.job_type, final_status)


def heartbeat_loop(stop_event: threading.Event) -> None:
    """Runs on its own thread, independent of the main BRPOP/execute loop, so
    a worker busy on a long job still reports itself alive on schedule.
    """
    while not stop_event.wait(settings.heartbeat_interval_seconds):
        db = SessionLocal()
        try:
            send_heartbeat(db, WORKER_ID)
        except Exception:
            logger.exception("heartbeat failed")
            db.rollback()
        finally:
            db.close()


def main() -> None:
    redis_client = get_redis_client()

    db = SessionLocal()
    try:
        register_worker(db, WORKER_ID, WORKER_SERIAL)
    finally:
        db.close()

    stop_event = threading.Event()
    threading.Thread(target=heartbeat_loop, args=(stop_event,), daemon=True).start()

    logger.info("worker %s started", WORKER_ID)
    while True:
        message = dequeue_execution(redis_client, timeout=settings.worker_poll_timeout_seconds)
        if message is None:
            continue

        db = SessionLocal()
        try:
            process_execution(db, uuid.UUID(message["execution_id"]))
        except Exception:
            logger.exception("failed to process execution %s", message.get("execution_id"))
            db.rollback()
        finally:
            db.close()


if __name__ == "__main__":
    main()
