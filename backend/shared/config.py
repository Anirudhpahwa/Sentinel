from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg2://sentinel:sentinel@localhost:5432/sentinel"
    redis_url: str = "redis://localhost:6379/0"
    job_queue_key: str = "sentinel:job_queue"
    scheduler_poll_interval_seconds: float = 5.0
    worker_poll_timeout_seconds: int = 5


settings = Settings()
