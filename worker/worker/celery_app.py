from celery import Celery
from celery.schedules import crontab

from worker.config import get_settings

settings = get_settings()

app = Celery(
    "mtbf_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["worker.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=settings.celery_task_track_started,
    task_time_limit=settings.celery_task_time_limit,
    worker_prefetch_multiplier=settings.celery_worker_prefetch_multiplier,
    worker_max_tasks_per_child=settings.celery_worker_max_tasks_per_child,
)

app.conf.beat_schedule = {
    "heartbeat-every-minute": {
        "task": "worker.tasks.heartbeat_task",
        "schedule": crontab(minute="*/1"),
    },
    "recompute-rolling-kpis-hourly": {
        "task": "worker.tasks.recompute_rolling_kpis_task",
        "schedule": crontab(
            minute=settings.kpi_rolling_schedule_minute,
            hour=settings.kpi_rolling_schedule_hour,
        ),
        "args": (None, "all", None),
    },
    "recompute-calendar-kpis-daily": {
        "task": "worker.tasks.recompute_calendar_kpis_task",
        "schedule": crontab(
            minute=settings.kpi_calendar_schedule_minute,
            hour=settings.kpi_calendar_schedule_hour,
        ),
        "args": (None, "all", None),
    },
    "data-quality-check-daily": {
        "task": "worker.tasks.data_quality_check_task",
        "schedule": crontab(minute=0, hour=2),  # Run daily at 2 AM UTC
        "args": (None, "comprehensive"),
    },
}

if __name__ == "__main__":
    app.start()
