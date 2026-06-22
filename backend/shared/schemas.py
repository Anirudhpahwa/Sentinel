import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class JobCreate(BaseModel):
    name: str
    description: str | None = None
    job_type: Literal["GENERATE_REPORT", "PROCESS_DATA", "SEND_NOTIFICATION"]
    payload: dict[str, Any] = Field(default_factory=dict)
    schedule_type: Literal["ONCE", "INTERVAL"]
    schedule_config: dict[str, Any]
    created_by: str = "anonymous"

    @model_validator(mode="after")
    def validate_schedule_config(self) -> "JobCreate":
        if self.schedule_type == "ONCE" and "run_at" not in self.schedule_config:
            raise ValueError("schedule_config must include 'run_at' for ONCE jobs")
        if self.schedule_type == "INTERVAL" and "interval_seconds" not in self.schedule_config:
            raise ValueError("schedule_config must include 'interval_seconds' for INTERVAL jobs")
        return self


class JobRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    description: str | None
    job_type: str
    payload: dict[str, Any]
    schedule_type: str
    schedule_config: dict[str, Any]
    next_run_at: datetime
    status: str
    created_by: str
    created_at: datetime
    updated_at: datetime


class JobExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    job_id: uuid.UUID
    status: str
    queued_at: datetime
    started_at: datetime | None
    completed_at: datetime | None
    result: dict[str, Any] | None
    worker_id: str | None


class ExecutionLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    execution_id: uuid.UUID
    timestamp: datetime
    level: str
    message: str


class WorkerRead(BaseModel):
    id: uuid.UUID
    worker_name: str
    status: str
    started_at: datetime
    last_heartbeat_at: datetime
    last_seen_at: datetime
    executions_completed: int
    executions_failed: int
