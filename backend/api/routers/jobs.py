import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.shared.audit import record_admin_action
from backend.shared.models import Job, JobExecution
from backend.shared.schemas import JobCreate, JobExecutionRead, JobRead
from backend.shared.scheduling import compute_initial_next_run

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.post("", response_model=JobRead, status_code=201)
def create_job(payload: JobCreate, db: Session = Depends(get_db)) -> Job:
    now = datetime.now(timezone.utc)
    next_run_at = compute_initial_next_run(payload.schedule_type, payload.schedule_config, now)

    job = Job(
        name=payload.name,
        description=payload.description,
        job_type=payload.job_type,
        payload=payload.payload,
        schedule_type=payload.schedule_type,
        schedule_config=payload.schedule_config,
        next_run_at=next_run_at,
        created_by=payload.created_by,
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@router.get("", response_model=list[JobRead])
def list_jobs(db: Session = Depends(get_db)) -> list[Job]:
    return list(
        db.execute(select(Job).where(Job.deleted_at.is_(None)).order_by(Job.created_at.desc())).scalars().all()
    )


@router.get("/{job_id}", response_model=JobRead)
def get_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return job


@router.get("/{job_id}/executions", response_model=list[JobExecutionRead])
def list_job_executions(job_id: uuid.UUID, db: Session = Depends(get_db)) -> list[JobExecution]:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return list(
        db.execute(
            select(JobExecution).where(JobExecution.job_id == job_id).order_by(JobExecution.queued_at.desc())
        )
        .scalars()
        .all()
    )


@router.delete("/{job_id}", response_model=JobRead)
def delete_job(job_id: uuid.UUID, db: Session = Depends(get_db)) -> Job:
    job = db.get(Job, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.deleted_at is None:
        job.deleted_at = datetime.now(timezone.utc)
        db.commit()
        record_admin_action(db, action="DELETE_JOB", target_type="job", target_id=str(job_id), detail=job.name)
    return job
