from enum import Enum


class JobStatus(str, Enum):
    """Lifecycle of a job's schedule (not its executions)."""

    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class ExecutionStatus(str, Enum):
    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class ScheduleType(str, Enum):
    """Stored as plain text in the DB, not a native Postgres enum, so new
    values (CRON, DAILY, WEEKLY, ...) can be added later without a migration.
    """

    ONCE = "ONCE"
    INTERVAL = "INTERVAL"


class JobType(str, Enum):
    GENERATE_REPORT = "GENERATE_REPORT"
    PROCESS_DATA = "PROCESS_DATA"
    SEND_NOTIFICATION = "SEND_NOTIFICATION"


class LogLevel(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"


class WorkerStatus(str, Enum):
    """Computed solely by the health monitor from heartbeat staleness --
    workers never set their own status past the bootstrap HEALTHY they
    write at registration.
    """

    HEALTHY = "HEALTHY"
    UNHEALTHY = "UNHEALTHY"
    OFFLINE = "OFFLINE"
