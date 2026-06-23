from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.routers.schedulers import STALE_AFTER_SECONDS
from backend.shared.audit import record_admin_action
from backend.shared.enums import WorkerStatus
from backend.shared.models import AdminAction, Job, JobExecution, Scheduler, Worker
from backend.shared.schemas import AdminActionRead, ResetConfirmation, ResetSummary

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/actions", response_model=list[AdminActionRead])
def list_admin_actions(
    limit: int = Query(default=50, ge=1, le=500), db: Session = Depends(get_db)
) -> list[AdminAction]:
    return list(
        db.execute(select(AdminAction).order_by(AdminAction.performed_at.desc()).limit(limit)).scalars().all()
    )


@router.post("/reset-demo-environment", response_model=ResetSummary)
def reset_demo_environment(payload: ResetConfirmation, db: Session = Depends(get_db)) -> ResetSummary:
    db_now = db.execute(select(func.now())).scalar_one()

    jobs_deleted = db.execute(select(func.count()).select_from(Job)).scalar_one()
    executions_deleted = db.execute(select(func.count()).select_from(JobExecution)).scalar_one()

    # Hard delete here, unlike the normal per-job soft delete: the point of
    # a demo reset is an actually-clean slate, not an ever-growing pile of
    # soft-deleted rows. Cascades to job_executions -> execution_logs via
    # the existing FKs, so a single statement is correct and sufficient.
    db.execute(Job.__table__.delete())

    # Workers/schedulers are still never deleted -- only the ones that are
    # already gone (OFFLINE / stale) get archived. One that's currently
    # healthy and running is not demo cruft; archiving it would just be
    # wrong, not merely unnecessary.
    workers_archived = db.execute(
        update(Worker)
        .where(Worker.archived_at.is_(None), Worker.status == WorkerStatus.OFFLINE)
        .values(archived_at=db_now)
    ).rowcount

    schedulers_archived = db.execute(
        update(Scheduler)
        .where(
            Scheduler.archived_at.is_(None),
            func.extract("epoch", db_now - Scheduler.last_seen_at) > STALE_AFTER_SECONDS,
        )
        .values(archived_at=db_now)
    ).rowcount

    db.commit()

    record_admin_action(
        db,
        action="RESET_DEMO_ENVIRONMENT",
        target_type="platform",
        detail=(
            f"jobs_deleted={jobs_deleted} executions_deleted={executions_deleted} "
            f"workers_archived={workers_archived} schedulers_archived={schedulers_archived}"
        ),
    )

    return ResetSummary(
        jobs_deleted=jobs_deleted,
        executions_deleted=executions_deleted,
        workers_archived=workers_archived,
        schedulers_archived=schedulers_archived,
        performed_at=db_now,
    )
