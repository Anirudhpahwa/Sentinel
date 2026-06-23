import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import ForeignKey, Index, String, TIMESTAMP, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.shared.db import Base
from backend.shared.enums import ExecutionStatus, JobStatus, LogLevel, WorkerStatus


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    job_type: Mapped[str] = mapped_column(String(50), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)

    # Schedule is split into a discriminator + opaque config so new schedule
    # types (CRON, DAILY, WEEKLY, ...) can be added later without touching
    # this table. next_run_at is the one materialized, indexed timestamp the
    # scheduler actually polls on, regardless of how it was derived.
    schedule_type: Mapped[str] = mapped_column(String(50), nullable=False)
    schedule_config: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    next_run_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    status: Mapped[str] = mapped_column(String(50), nullable=False, default=JobStatus.ACTIVE)
    created_by: Mapped[str] = mapped_column(String(255), nullable=False, default="anonymous")
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    executions: Mapped[list["JobExecution"]] = relationship(back_populates="job")

    __table_args__ = (Index("ix_jobs_status_next_run_at", "status", "next_run_at"),)


class JobExecution(Base):
    __tablename__ = "job_executions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=ExecutionStatus.QUEUED)
    queued_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Retry tracking: root_execution_id points at the first attempt's own id
    # (every fresh, non-retry row points at itself), so the whole attempt
    # chain for one logical run is a single flat query on this column rather
    # than a linked-list walk. abandoned_reason is set only by the recovery
    # service, alongside a matching execution_log entry -- the column gives
    # quick structured display, the log gives the timestamped narrative.
    attempt_number: Mapped[int] = mapped_column(nullable=False, default=1)
    max_attempts: Mapped[int] = mapped_column(nullable=False, default=3)
    root_execution_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("job_executions.id", ondelete="CASCADE"), nullable=True
    )
    abandoned_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Added for Phase 4 metrics: the only timestamp marking *when* a row last
    # changed terminal state (e.g. when it was abandoned), since abandonment
    # has no dedicated timestamp column of its own.
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    job: Mapped["Job"] = relationship(back_populates="executions")
    logs: Mapped[list["ExecutionLog"]] = relationship(
        back_populates="execution", order_by="ExecutionLog.timestamp"
    )

    __table_args__ = (
        Index("ix_job_executions_job_id_queued_at", "job_id", "queued_at"),
        Index("ix_job_executions_worker_id", "worker_id"),
        Index("ix_job_executions_root_execution_id", "root_execution_id"),
        Index("ix_job_executions_status", "status"),
        Index("ix_job_executions_completed_at", "completed_at"),
        Index("ix_job_executions_queued_at", "queued_at"),
    )


class ExecutionLog(Base):
    __tablename__ = "execution_logs"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    execution_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("job_executions.id", ondelete="CASCADE"), nullable=False
    )
    timestamp: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    level: Mapped[str] = mapped_column(String(20), nullable=False, default=LogLevel.INFO)
    message: Mapped[str] = mapped_column(Text, nullable=False)

    execution: Mapped["JobExecution"] = relationship(back_populates="logs")

    __table_args__ = (Index("ix_execution_logs_execution_id_timestamp", "execution_id", "timestamp"),)


class Worker(Base):
    __tablename__ = "workers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    worker_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default=WorkerStatus.HEALTHY)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    # Set from the WORKER_SERIAL env var (assigned explicitly per service in
    # docker-compose, since deploy.replicas cannot give replicas distinct
    # identities outside Swarm). Nullable: local/non-Compose runs won't have
    # it, and worker_name (the hostname) remains the real identity key
    # everywhere else -- this is purely a human-friendly terminal reference.
    worker_serial: Mapped[int | None] = mapped_column(nullable=True)

    # last_heartbeat_at is touched only by the worker's dedicated heartbeat
    # thread and is the sole input to health-state computation. last_seen_at
    # is touched by that same thread *and* by job-claim/completion, so a
    # divergence between the two (heartbeat stale, last_seen fresh) is itself
    # a meaningful signal: the heartbeat thread died but the worker is still
    # processing jobs.
    last_heartbeat_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)

    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    __table_args__ = (Index("ix_workers_status", "status"),)


class SchedulerLeadership(Base):
    """Singleton lease row -- exactly one logical lock, named so a future
    second lock (e.g. for a different coordinator role) wouldn't require a
    schema change. acquired_at/term only change when leadership actually
    moves to a new holder; last_renewed_at changes every successful tick.
    """

    __tablename__ = "scheduler_leadership"

    lock_name: Mapped[str] = mapped_column(String(50), primary_key=True)
    leader_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    term: Mapped[int] = mapped_column(nullable=False, default=0)
    acquired_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    lease_expires_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    last_renewed_at: Mapped[datetime | None] = mapped_column(TIMESTAMP(timezone=True), nullable=True)


class Scheduler(Base):
    """Per-instance registry, mirroring the Worker pattern -- every scheduler
    process (leader or follower) heartbeats its own row here, which is the
    only way to answer "how many schedulers exist" (the leadership row only
    describes the leader, not idle followers).
    """

    __tablename__ = "schedulers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    scheduler_name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    is_leader: Mapped[bool] = mapped_column(nullable=False, default=False)
    failed_election_attempts: Mapped[int] = mapped_column(nullable=False, default=0)
    started_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), server_default=func.now(), onupdate=func.now()
    )


class SchedulerElection(Base):
    """Append-only history: one row per time leadership actually changed
    hands (not per renewal), giving "Recent Elections" and election-rate
    metrics directly from a COUNT/LIST query.
    """

    __tablename__ = "scheduler_elections"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    term: Mapped[int] = mapped_column(nullable=False)
    leader_id: Mapped[str] = mapped_column(String(255), nullable=False)
    elected_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True), server_default=func.now())

    __table_args__ = (Index("ix_scheduler_elections_elected_at", "elected_at"),)
