from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.metrics.schemas import JobMetrics
from backend.metrics.window import recent_cutoff
from backend.shared.enums import ExecutionStatus, JobStatus
from backend.shared.models import Job, JobExecution


def compute_job_metrics(db: Session) -> JobMetrics:
    total_jobs = db.execute(select(func.count()).select_from(Job)).scalar_one()
    active_jobs = db.execute(
        select(func.count()).select_from(Job).where(Job.status == JobStatus.ACTIVE)
    ).scalar_one()
    completed_jobs = db.execute(
        select(func.count()).select_from(Job).where(Job.status == JobStatus.COMPLETED)
    ).scalar_one()

    # jobs.status only tracks the schedule (ACTIVE/COMPLETED), not outcomes --
    # "failed" is derived from the execution side: any job with at least one
    # execution that never recovered into a success.
    failed_jobs = db.execute(
        select(func.count(func.distinct(JobExecution.job_id))).where(
            JobExecution.status.in_([ExecutionStatus.FAILED, ExecutionStatus.PERMANENTLY_FAILED])
        )
    ).scalar_one()

    cutoff = recent_cutoff(db)
    jobs_created_recent = db.execute(
        select(func.count()).select_from(Job).where(Job.created_at >= cutoff)
    ).scalar_one()

    return JobMetrics(
        total_jobs=total_jobs,
        active_jobs=active_jobs,
        completed_jobs=completed_jobs,
        failed_jobs=failed_jobs,
        jobs_created_recent=jobs_created_recent,
    )
