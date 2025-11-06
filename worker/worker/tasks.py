import logging
from datetime import datetime

from worker.celery_app import app

logger = logging.getLogger(__name__)


@app.task(name="worker.tasks.heartbeat_task")
def heartbeat_task():
    timestamp = datetime.utcnow().isoformat()
    logger.info(f"Worker heartbeat at {timestamp}")
    return {"status": "alive", "timestamp": timestamp}


@app.task(name="worker.tasks.example_task")
def example_task(x: int, y: int):
    logger.info(f"Running example task with x={x}, y={y}")
    result = x + y
    logger.info(f"Example task result: {result}")
    return result
