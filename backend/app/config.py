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

    # Application
    app_name: str = "MTBF Platform"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "development"

    # Database
    database_url: PostgresDsn = "postgresql://postgres:postgres@postgres:5432/mtbf"

    # Redis
    redis_url: RedisDsn = "redis://redis:6379/0"

    # Celery
    celery_broker_url: str = "redis://redis:6379/0"
    celery_result_backend: str = "redis://redis:6379/0"

    # API
    api_prefix: str = "/api"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # JWT Authentication
    jwt_secret: str = "your-super-secret-key-change-in-production"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

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
