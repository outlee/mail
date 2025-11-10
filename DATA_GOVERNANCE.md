# Data Governance Implementation

This document describes the data governance features implemented in the MTBF platform.

## Overview

The data governance implementation provides:

1. **Data Quality Validations** - Ensuring data integrity and consistency
2. **Audit Logging** - Tracking all data modifications with full history
3. **Observability** - Prometheus metrics and OpenTelemetry tracing
4. **Automated Data Quality Checks** - Daily Celery tasks for integrity validation

## Data Models

### AssetRuntime
Tracks runtime counters for assets with monotonic validation:
- `runtime_counter`: Must be monotonically increasing per asset
- `recorded_at`: Timestamp of the runtime measurement
- `metadata`: Optional additional information

### FailureEvent
Records failure events with temporal validation:
- `severity`: LOW, MEDIUM, HIGH, CRITICAL
- `start_time`/`end_time`: Non-overlapping time windows required
- `description`: Required, with detailed descriptions for HIGH/CRITICAL severity

### AuditLogEntry
Comprehensive audit trail for all modifications:
- `action`: CREATE, UPDATE, DELETE
- `resource_type`: Type of entity modified
- `old_values`/`new_values`: JSON snapshots before/after changes
- `ip_address`: Client IP address for security

### DataQualityReport
Results of automated data quality checks:
- `report_type`: Type of check performed
- `status`: pending, running, completed, failed
- `issues_found`: Number of issues detected
- `details`: Full breakdown of issues found

## API Endpoints

### Asset Runtime Management
- `POST /api/v1/asset-runtimes/` - Create runtime entry
- `GET /api/v1/asset-runtimes/{runtime_id}` - Get specific runtime
- `GET /api/v1/asset-runtimes/asset/{asset_id}` - List asset runtimes

### Failure Event Management
- `POST /api/v1/failure-events/` - Create failure event
- `GET /api/v1/failure-events/{event_id}` - Get specific event
- `PUT /api/v1/failure-events/{event_id}` - Update failure event
- `DELETE /api/v1/failure-events/{event_id}` - Delete failure event
- `GET /api/v1/failure-events/` - List failure events

### Audit Log
- `GET /api/v1/audit/` - List audit entries (MAINTAINER/MANAGER only)

### Data Quality
- `POST /api/v1/data-quality/check` - Run data quality check
- `GET /api/v1/data-quality/reports` - List quality reports
- `GET /api/v1/data-quality/reports/{report_id}` - Get specific report

## Validations

### Runtime Counter Validation
- Runtime counters must be monotonically increasing per asset
- Attempting to insert a decreasing counter raises ValueError
- Validation occurs at both Pydantic and SQLAlchemy levels

### Failure Event Validation
- Time windows cannot overlap for the same asset
- End time must be after start time
- HIGH/CRITICAL severity events require detailed descriptions (min 10 chars)

### Data Quality Checks
The automated daily check validates:
1. Assets without runtime entries
2. Failure events with invalid time windows
3. Assets with decreasing runtime counters

## Observability

### Prometheus Metrics
Available at `http://localhost:8000/metrics`:

- `api_requests_total` - API request count by method, endpoint, status
- `api_request_duration_seconds` - Request latency by method, endpoint
- `validation_failures_total` - Validation failures by type and resource
- `task_duration_seconds` - Celery task execution times
- `task_success_total` / `task_failure_total` - Task outcomes
- `data_quality_issues_found` - Current issue count by report type
- `audit_log_entries_total` - Audit entry count by action and resource

### OpenTelemetry Tracing
- Automatic instrumentation for FastAPI and SQLAlchemy
- Custom tracing decorators for business operations
- Distributed tracing for microservices communication

### Grafana Dashboards
Pre-configured dashboards available at `http://localhost:3000`:
- API Performance Dashboard
- Data Quality Dashboard
- System Health Dashboard

Default credentials: admin/admin

## Celery Tasks

### Daily Data Quality Check
Runs every day at 2 AM UTC:
```python
# Manual trigger
from worker.tasks import data_quality_check_task
data_quality_check_task.delay(None, "comprehensive")
```

### Task Monitoring
All data quality tasks create TaskRun entries for monitoring:
- Status tracking (PENDING → RUNNING → SUCCESS/FAILED)
- Error logging and retry logic
- Completion metadata

## Security

### Role-Based Access Control
- **MAINTAINER**: Full access to all features
- **OPERATOR**: Can create/update runtime and failure events
- **MANAGER**: Read-only access to audit logs and reports

### Audit Trail
All modifications are automatically logged with:
- User identification
- Action performed
- Before/after data snapshots
- IP address tracking
- Timestamp

## Configuration

### Environment Variables
```bash
# Data Quality Schedule (optional)
DATA_QUALITY_SCHEDULE_MINUTE=0
DATA_QUALITY_SCHEDULE_HOUR=2

# Observability
OTEL_SERVICE_NAME=mtbf-api
OTEL_EXPORTER_PROMETHEUS_ENDPOINT=http://prometheus:9090
```

### Docker Services
- **Prometheus**: `http://localhost:9090` - Metrics collection
- **Grafana**: `http://localhost:3000` - Visualization dashboards

## Testing

### Unit Tests
```bash
cd backend
python -m pytest tests/test_data_governance.py -v
```

### Integration Tests
```bash
# Start services
docker compose up --build

# Run data quality check
curl -X POST http://localhost:8000/api/v1/data-quality/check \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"

# View metrics
curl http://localhost:8000/metrics
```

## Troubleshooting

### Common Issues

1. **Validation Failures**
   - Check for overlapping failure events
   - Verify monotonic runtime counters
   - Ensure high-severity events have detailed descriptions

2. **Data Quality Check Failures**
   - Review task run logs: `docker compose logs worker`
   - Check database connectivity
   - Verify model imports in worker

3. **Metrics Not Appearing**
   - Confirm Prometheus configuration
   - Check `/metrics` endpoint accessibility
   - Verify OpenTelemetry instrumentation

### Performance Considerations

1. **Audit Log Growth**
   - Implement log rotation policies
   - Consider archiving old entries
   - Add indexes for common queries

2. **Data Quality Check Performance**
   - Batch process large datasets
   - Use database indexes effectively
   - Consider incremental checks

## Future Enhancements

1. **Anomaly Detection**
   - Machine learning for unusual patterns
   - Automated alerting on anomalies
   - Trend analysis and forecasting

2. **Advanced Auditing**
   - Change approval workflows
   - Electronic signatures
   - Compliance reporting

3. **Enhanced Observability**
   - Custom business metrics
   - Real-time alerting
   - Integration with external monitoring systems