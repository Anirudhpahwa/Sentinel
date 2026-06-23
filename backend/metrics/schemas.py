from datetime import datetime

from pydantic import BaseModel


class JobMetrics(BaseModel):
    total_jobs: int
    active_jobs: int
    completed_jobs: int
    failed_jobs: int
    jobs_created_recent: int


class ExecutionMetrics(BaseModel):
    executions_recent: int
    executions_last_hour: int
    successful_executions_recent: int
    failed_executions_recent: int
    average_duration_seconds: float | None
    p95_duration_seconds: float | None
    current_running: int


class WorkerMetrics(BaseModel):
    total_workers: int
    healthy_workers: int
    unhealthy_workers: int
    offline_workers: int
    utilization_percent: float


class RecoveryMetrics(BaseModel):
    recovery_attempts_recent: int
    recovery_successes_recent: int
    recovery_failures_recent: int
    abandoned_executions_recent: int
    requeued_executions_recent: int
    recovery_success_rate_percent: float | None


class QueueMetrics(BaseModel):
    queue_depth: int
    oldest_pending_age_seconds: float | None
    average_wait_seconds: float | None


class OverviewMetrics(BaseModel):
    active_jobs: int
    healthy_workers: int
    queue_depth: int
    executions_recent: int
    success_rate_percent: float | None
    recovery_count_recent: int


class TrendBucket(BaseModel):
    bucket_start: datetime
    executions: int
    failures: int
    recoveries: int


class TrendsResponse(BaseModel):
    window_hours: int
    buckets: list[TrendBucket]


class SchedulerMetrics(BaseModel):
    current_leader: str | None
    leader_since: datetime | None
    leader_uptime_seconds: float | None
    active_schedulers: int
    leader_elections_total: int
    leadership_changes_recent: int
    failed_election_attempts_total: int
