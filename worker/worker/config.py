from functools import lru_cache

from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Celery
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"
    celery_task_always_eager: bool = False
    celery_task_track_started: bool = True
    celery_task_time_limit: int = 30 * 60
    celery_worker_prefetch_multiplier: int = 4
    celery_worker_max_tasks_per_child: int = 1000

    # Application
    app_name: str = "MTBF Worker"
    environment: str = "development"

    # Database
    database_url: PostgresDsn = "postgresql://postgres:postgres@postgres:5432/mtbf"

    # KPI Scheduling
    kpi_rolling_schedule_minute: str = "*"
    kpi_rolling_schedule_hour: str = "*"
    kpi_calendar_schedule_minute: str = "0"
    kpi_calendar_schedule_hour: str = "0"
    kpi_batch_size: int = 100

    # CSV Imports
    csv_import_max_bytes: int = 5 * 1024 * 1024
    csv_import_storage_path: str = "./tmp/csv_imports"
    csv_import_idempotency_ttl_minutes: int = 60
    csv_import_error_sample_size: int = 10


@lru_cache()
def get_settings() -> Settings:
    return Settings()
