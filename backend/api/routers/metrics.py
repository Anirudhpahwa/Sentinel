import redis
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db, get_redis
from backend.metrics.executions import compute_execution_metrics
from backend.metrics.jobs import compute_job_metrics
from backend.metrics.overview import compute_overview
from backend.metrics.queue import compute_queue_metrics
from backend.metrics.recovery import compute_recovery_metrics
from backend.metrics.schemas import (
    ExecutionMetrics,
    JobMetrics,
    OverviewMetrics,
    QueueMetrics,
    RecoveryMetrics,
    TrendsResponse,
    WorkerMetrics,
)
from backend.metrics.trends import compute_trends
from backend.metrics.workers import compute_worker_metrics

router = APIRouter(prefix="/metrics", tags=["metrics"])


@router.get("/overview", response_model=OverviewMetrics)
def get_overview(db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)) -> OverviewMetrics:
    return compute_overview(db, redis_client)


@router.get("/jobs", response_model=JobMetrics)
def get_job_metrics(db: Session = Depends(get_db)) -> JobMetrics:
    return compute_job_metrics(db)


@router.get("/executions", response_model=ExecutionMetrics)
def get_execution_metrics(db: Session = Depends(get_db)) -> ExecutionMetrics:
    return compute_execution_metrics(db)


@router.get("/workers", response_model=WorkerMetrics)
def get_worker_metrics(db: Session = Depends(get_db)) -> WorkerMetrics:
    return compute_worker_metrics(db)


@router.get("/recovery", response_model=RecoveryMetrics)
def get_recovery_metrics(db: Session = Depends(get_db)) -> RecoveryMetrics:
    return compute_recovery_metrics(db)


@router.get("/queue", response_model=QueueMetrics)
def get_queue_metrics(
    db: Session = Depends(get_db), redis_client: redis.Redis = Depends(get_redis)
) -> QueueMetrics:
    return compute_queue_metrics(db, redis_client)


@router.get("/trends", response_model=TrendsResponse)
def get_trends(hours: int = Query(default=24, ge=1, le=168), db: Session = Depends(get_db)) -> TrendsResponse:
    return compute_trends(db, hours)
