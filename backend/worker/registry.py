"""Worker self-registration and heartbeats. This module only ever writes
last_heartbeat_at, last_seen_at, started_at -- never `status`. Status is
computed exclusively by the health monitor from heartbeat staleness.
"""

from datetime import datetime, timezone

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from backend.shared.enums import WorkerStatus
from backend.shared.models import Worker


def register_worker(db: Session, worker_name: str) -> None:
    now = datetime.now(timezone.utc)
    stmt = (
        pg_insert(Worker)
        .values(
            worker_name=worker_name,
            status=WorkerStatus.HEALTHY,
            started_at=now,
            last_heartbeat_at=now,
            last_seen_at=now,
        )
        .on_conflict_do_update(
            index_elements=[Worker.worker_name],
            set_={
                "started_at": now,
                "last_heartbeat_at": now,
                "last_seen_at": now,
                "updated_at": now,
            },
        )
    )
    db.execute(stmt)
    db.commit()


def send_heartbeat(db: Session, worker_name: str) -> None:
    now = datetime.now(timezone.utc)
    db.execute(
        update(Worker)
        .where(Worker.worker_name == worker_name)
        .values(last_heartbeat_at=now, last_seen_at=now, updated_at=now)
    )
    db.commit()


def touch_last_seen(db: Session, worker_name: str) -> None:
    db.execute(
        update(Worker)
        .where(Worker.worker_name == worker_name)
        .values(last_seen_at=datetime.now(timezone.utc))
    )
    db.commit()
