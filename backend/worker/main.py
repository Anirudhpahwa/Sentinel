import logging
import socket
import threading
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from backend.shared.config import settings
from backend.shared.db import SessionLocal
from backend.shared.enums import ExecutionStatus, LogLevel
from backend.shared.models import ExecutionLog, Job, JobExecution
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


def write_log(db: Session, execution_id: uuid.UUID, message: str, level: str = LogLevel.INFO) -> None:
    db.add(ExecutionLog(execution_id=execution_id, message=message, level=level))
    db.commit()


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

    write_log(db, execution.id, "Starting execution")
    write_log(db, execution.id, "Loading configuration")

    result, succeeded = simulate_job(job.job_type, job.payload, lambda msg: write_log(db, execution.id, msg))

    execution.status = ExecutionStatus.SUCCEEDED if succeeded else ExecutionStatus.FAILED
    execution.completed_at = datetime.now(timezone.utc)
    execution.result = result
    db.commit()
    touch_last_seen(db, WORKER_ID)

    write_log(
        db,
        execution.id,
        "Execution completed" if succeeded else "Execution failed",
        level=LogLevel.INFO if succeeded else LogLevel.ERROR,
    )

    logger.info("execution %s (%s) finished: %s", execution.id, job.job_type, execution.status)


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
        register_worker(db, WORKER_ID)
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
