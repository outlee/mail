# KPI Scheduling and Task Management

This document describes the Celery Beat scheduling system for KPI computation in the MTBF Platform.

## Overview

The platform uses Celery Beat to schedule periodic tasks for computing Key Performance Indicators (KPIs) across assets and groups. The system includes:

- **Scheduled Tasks**: Automated hourly rolling KPI and daily calendar KPI computations
- **Manual Triggers**: API endpoints to trigger on-demand KPI recomputation
- **Task Tracking**: Database persistence of task execution metadata
- **Concurrency Control**: PostgreSQL advisory locks prevent overlapping computations

## Architecture

### Components

1. **Celery Scheduler** (`scheduler` service): Celery Beat process that triggers scheduled tasks
2. **Celery Worker** (`worker` service): Processes KPI computation tasks
3. **Backend API** (`api` service): Provides REST endpoints for manual task triggering
4. **Database**: Stores KPI snapshots, task runs, and audit information

### Key Models

- **KPISnapshot**: Records computed KPI values with timestamps
- **TaskRun**: Tracks task execution metadata (status, start/end times, errors)
- **Asset**: Individual entities for which KPIs are computed
- **Group**: Collections of assets for aggregated KPI tracking

## Configuration

### Environment Variables

Configure scheduling behavior through environment variables in `.env`:

```bash
# Celery broker and result backend
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# KPI Scheduling (cron format: minute hour)
KPI_ROLLING_SCHEDULE_MINUTE=*           # Every minute (hourly every minute)
KPI_ROLLING_SCHEDULE_HOUR=*             # Every hour
KPI_CALENDAR_SCHEDULE_MINUTE=0          # At minute 0
KPI_CALENDAR_SCHEDULE_HOUR=0            # At hour 0 (daily at midnight UTC)

# Task processing
KPI_BATCH_SIZE=100                      # Number of assets/groups per batch
```

### Schedule Examples

| Use Case | Configuration |
|----------|---|
| Every hour | `KPI_ROLLING_SCHEDULE_MINUTE=0` `KPI_ROLLING_SCHEDULE_HOUR=*` |
| Every 4 hours | `KPI_ROLLING_SCHEDULE_MINUTE=0` `KPI_ROLLING_SCHEDULE_HOUR=*/4` |
| Every 30 minutes | `KPI_ROLLING_SCHEDULE_MINUTE=*/30` `KPI_ROLLING_SCHEDULE_HOUR=*` |
| Daily at 2 AM UTC | `KPI_CALENDAR_SCHEDULE_MINUTE=0` `KPI_CALENDAR_SCHEDULE_HOUR=2` |

See [crontab documentation](https://en.wikipedia.org/wiki/Cron) for more cron expression examples.

## Scheduled Tasks

### Rolling KPIs (Hourly)

**Task**: `worker.tasks.recompute_rolling_kpis_task`

Recomputes rolling window KPIs for all assets. These typically represent metrics over short time windows.

- **Schedule**: Configurable via `KPI_ROLLING_SCHEDULE_*`
- **Default**: Every hour at minute 0
- **Scope**: All assets
- **Lock**: Per-asset advisory lock to prevent concurrent recomputation

### Calendar KPIs (Daily)

**Task**: `worker.tasks.recompute_calendar_kpis_task`

Recomputes calendar period KPIs (daily, weekly, monthly) for all groups.

- **Schedule**: Configurable via `KPI_CALENDAR_SCHEDULE_*`
- **Default**: Daily at 00:00 UTC
- **Scope**: All groups
- **Lock**: Per-group advisory lock to prevent concurrent recomputation

## Manual Task Triggering

### Endpoint

```
POST /api/v1/kpis/recompute
Authorization: Bearer {access_token}
```

### Request Payload

```json
{
  "scope": "all_assets",
  "asset_id": null,
  "group_id": null
}
```

### Scope Options

| Scope | Description | Required Fields |
|-------|---|---|
| `all_assets` | Recompute rolling KPIs for all assets | None |
| `single_asset` | Recompute rolling KPI for specific asset | `asset_id` |
| `all_groups` | Recompute calendar KPIs for all groups | None |
| `single_group` | Recompute calendar KPI for specific group | `group_id` |

### Response

```json
{
  "id": "task-run-uuid",
  "task_name": "recompute_kpis",
  "task_id": "celery-task-uuid",
  "status": "pending",
  "scope": "all_assets",
  "asset_id": null,
  "group_id": null,
  "started_at": null,
  "completed_at": null,
  "error_message": null,
  "items_processed": 0,
  "created_at": "2024-01-15T10:30:00Z"
}
```

### Check Task Status

```
GET /api/v1/kpis/task-runs/{task_run_id}
Authorization: Bearer {access_token}
```

Returns the `TaskRun` object with current execution status and results.

## Task Execution Flow

1. **Schedule**: Celery Beat triggers task at configured schedule or manual trigger
2. **Create TaskRun**: Backend creates a `TaskRun` record with `PENDING` status
3. **Enqueue**: Task sent to worker queue with retry policy (3 retries, exponential backoff)
4. **Execute**:
   - Worker acquires advisory lock for target (asset/group)
   - KPI service performs computation
   - Updates `TaskRun` with `RUNNING` status and start time
5. **Complete**:
   - On success: `TaskRun` status → `SUCCESS`, items_processed recorded
   - On error: `TaskRun` status → `FAILED`, error message saved
   - Lock released
   - Task retried if configured (up to max retries)

## Concurrency Control

The system uses PostgreSQL advisory locks to prevent overlapping recomputation of the same asset/group:

```python
# Lock ID derived from asset/group ID
lock_id = KPIService._generate_lock_id("kpi", asset_id)

# Acquire lock before recomputation
if KPIService.acquire_lock(db, lock_id):
    try:
        # Perform recomputation
        KPIService.recompute_asset_kpis(db, asset_id, ...)
    finally:
        # Always release lock
        KPIService.release_lock(db, lock_id)
```

Benefits:
- **Idempotency**: Same asset never computed concurrently
- **Data Integrity**: Prevents race conditions and duplicate snapshots
- **Distributed**: Works across multiple workers

## Monitoring

### Logs

Monitor task execution through container logs:

```bash
# Scheduler logs (see scheduled task triggers)
docker compose logs -f scheduler

# Worker logs (see task execution)
docker compose logs -f worker

# API logs (see manual triggers)
docker compose logs -f api
```

### Database Queries

Query task execution history:

```sql
-- Recent task runs
SELECT id, task_name, status, started_at, completed_at, items_processed
FROM task_runs
ORDER BY created_at DESC
LIMIT 10;

-- Failed tasks
SELECT id, task_name, error_message, completed_at
FROM task_runs
WHERE status = 'failed'
ORDER BY created_at DESC;

-- Task duration statistics
SELECT 
  task_name, 
  status,
  AVG(EXTRACT(EPOCH FROM (completed_at - started_at))) as avg_duration_seconds,
  MAX(EXTRACT(EPOCH FROM (completed_at - started_at))) as max_duration_seconds
FROM task_runs
WHERE completed_at IS NOT NULL
GROUP BY task_name, status;

-- Recent KPI snapshots
SELECT asset_id, kpi_type, value, period_start, created_at
FROM kpi_snapshots
ORDER BY created_at DESC
LIMIT 20;
```

## Error Handling

### Retry Policy

Tasks implement exponential backoff retry:
- Max retries: 3
- Initial delay: 1 second
- Step increase: 2x per retry
- Maximum delay: 10 seconds

### Common Errors

| Error | Cause | Resolution |
|-------|-------|---|
| Lock acquisition failed | Concurrent recomputation attempt | Automatic retry (built-in) |
| Asset/Group not found | Deleted before task execution | Logged and skipped |
| Database connection error | Network or DB down | Task retries automatically |
| Advisory lock timeout | Lock held by another process | Logged and retried |

## Testing

### Run Tests

```bash
# Backend KPI tests
cd backend
pytest tests/test_kpi_scheduling.py -v

# Worker task tests (requires test database)
cd worker
pytest tests/test_kpi_tasks.py -v
```

### Test Database Setup

The test suite uses a dedicated test database. Configure in `conftest.py`:

```python
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/mtbf_test"
```

## Troubleshooting

### Tasks Not Executing

1. **Check scheduler is running**:
   ```bash
   docker compose ps scheduler
   ```

2. **Verify Redis connection**:
   ```bash
   docker compose exec redis redis-cli ping
   ```

3. **Check for scheduling errors** in scheduler logs:
   ```bash
   docker compose logs scheduler | grep -i error
   ```

### Tasks Stuck or Running Long

1. **Check active tasks**:
   ```bash
   docker compose exec worker celery -A worker.celery_app inspect active
   ```

2. **Query task_runs table**:
   ```sql
   SELECT * FROM task_runs 
   WHERE status = 'running' 
   AND started_at < NOW() - INTERVAL '1 hour';
   ```

3. **Check PostgreSQL locks**:
   ```sql
   SELECT * FROM pg_locks WHERE locktype = 'advisory';
   ```

### High Memory Usage

Reduce batch size if processing large datasets:

```bash
# In .env
KPI_BATCH_SIZE=50  # Instead of default 100
```

## Future Enhancements

- **Airflow Integration**: Use Apache Airflow for complex scheduling
- **SLA Monitoring**: Alert if task duration exceeds threshold
- **OpenTelemetry Metrics**: Export metrics to collectors
- **Distributed Tracing**: Track task execution across services
- **Grafana Dashboards**: Visualize KPI computation metrics
- **Adaptive Scheduling**: Adjust schedule based on historical performance

## Related Documentation

- [README.md](README.md) - Project overview
- [VERIFICATION.md](VERIFICATION.md) - Testing procedures
- [docker-compose.yml](docker-compose.yml) - Service configuration
- [Celery Documentation](https://docs.celeryproject.io/)
- [Celery Beat Documentation](https://docs.celeryproject.io/en/stable/userguide/periodic-tasks.html)
