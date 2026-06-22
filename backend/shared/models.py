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

    job: Mapped["Job"] = relationship(back_populates="executions")
    logs: Mapped[list["ExecutionLog"]] = relationship(
        back_populates="execution", order_by="ExecutionLog.timestamp"
    )

    __table_args__ = (Index("ix_job_executions_job_id_queued_at", "job_id", "queued_at"),)


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
