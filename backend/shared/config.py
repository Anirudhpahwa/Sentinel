from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://sentinel:sentinel@localhost:5432/sentinel"
    redis_url: str = "redis://localhost:6379/0"
    job_queue_key: str = "sentinel:job_queue"
    scheduler_poll_interval_seconds: float = 5.0
    worker_poll_timeout_seconds: int = 5

    heartbeat_interval_seconds: float = 5.0
    health_check_interval_seconds: float = 5.0
    worker_healthy_threshold_seconds: float = 15.0
    worker_unhealthy_threshold_seconds: float = 30.0

    recovery_check_interval_seconds: float = 5.0
    default_max_attempts: int = 3

    # Single rolling-window knob shared by every "recent activity" metric
    # (executions, recovery counts, active worker fleet, ...) -- "Today"
    # throughout the metrics layer means "last N hours", not "since UTC
    # midnight", which avoids dashboards looking broken right after midnight.
    metrics_window_hours: int = 24

    # Renewed every scheduler tick (scheduler_poll_interval_seconds); a lease
    # of 3x the tick interval tolerates two missed renewals before another
    # instance can take over, avoiding flapping on transient jitter.
    leader_lease_seconds: float = 15.0


settings = Settings()
