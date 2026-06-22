import logging
import time

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.shared.config import settings
from backend.shared.db import SessionLocal
from backend.shared.enums import WorkerStatus
from backend.shared.models import Worker

logging.basicConfig(level=logging.INFO, format="%(asctime)s health-monitor %(levelname)s %(message)s")
logger = logging.getLogger("health-monitor")


def compute_status(age_seconds: float) -> str:
    if age_seconds < settings.worker_healthy_threshold_seconds:
        return WorkerStatus.HEALTHY
    if age_seconds < settings.worker_unhealthy_threshold_seconds:
        return WorkerStatus.UNHEALTHY
    return WorkerStatus.OFFLINE


def run_once(db: Session) -> int:
    # Heartbeat age is computed by Postgres itself (now() - last_heartbeat_at)
    # rather than compared against this service's local clock, so staleness
    # detection never depends on clock sync across containers.
    rows = db.execute(
        select(
            Worker.id,
            Worker.status,
            func.extract("epoch", func.now() - Worker.last_heartbeat_at),
        )
    ).all()

    changed = 0
    for worker_id, current_status, age_seconds in rows:
        new_status = compute_status(age_seconds)
        if new_status != current_status:
            db.execute(update(Worker).where(Worker.id == worker_id).values(status=new_status))
            logger.info(
                "worker %s: %s -> %s (heartbeat age %.1fs)", worker_id, current_status, new_status, age_seconds
            )
            changed += 1

    db.commit()
    return changed


def main() -> None:
    logger.info("health monitor started, polling every %ss", settings.health_check_interval_seconds)
    while True:
        db = SessionLocal()
        try:
            run_once(db)
        except Exception:
            logger.exception("health check tick failed")
            db.rollback()
        finally:
            db.close()
        time.sleep(settings.health_check_interval_seconds)


if __name__ == "__main__":
    main()
