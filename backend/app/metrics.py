import time
from typing import Dict, Any
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.metrics import set_meter_provider


# Prometheus Metrics
api_requests_total = Counter(
    'api_requests_total',
    'Total API requests',
    ['method', 'endpoint', 'status_code']
)

api_request_duration_seconds = Histogram(
    'api_request_duration_seconds',
    'API request duration in seconds',
    ['method', 'endpoint']
)

validation_failures_total = Counter(
    'validation_failures_total',
    'Total validation failures',
    ['validation_type', 'resource_type']
)

task_duration_seconds = Histogram(
    'task_duration_seconds',
    'Task execution duration in seconds',
    ['task_name', 'status']
)

task_success_total = Counter(
    'task_success_total',
    'Total successful task executions',
    ['task_name']
)

task_failure_total = Counter(
    'task_failure_total',
    'Total failed task executions',
    ['task_name', 'error_type']
)

data_quality_issues_found = Gauge(
    'data_quality_issues_found',
    'Number of data quality issues found',
    ['report_type']
)

audit_log_entries_total = Counter(
    'audit_log_entries_total',
    'Total audit log entries',
    ['action', 'resource_type']
)


def record_api_request(method: str, endpoint: str, status_code: int, duration: float):
    """Record API request metrics."""
    api_requests_total.labels(
        method=method,
        endpoint=endpoint,
        status_code=str(status_code)
    ).inc()
    api_request_duration_seconds.labels(
        method=method,
        endpoint=endpoint
    ).observe(duration)


def record_validation_failure(validation_type: str, resource_type: str):
    """Record validation failure."""
    validation_failures_total.labels(
        validation_type=validation_type,
        resource_type=resource_type
    ).inc()


def record_task_execution(task_name: str, status: str, duration: float, error_type: str = None):
    """Record task execution metrics."""
    task_duration_seconds.labels(
        task_name=task_name,
        status=status
    ).observe(duration)
    
    if status == 'success':
        task_success_total.labels(task_name=task_name).inc()
    else:
        task_failure_total.labels(
            task_name=task_name,
            error_type=error_type or 'unknown'
        ).inc()


def record_data_quality_issues(report_type: str, issues_count: int):
    """Record data quality issues."""
    data_quality_issues_found.labels(report_type=report_type).set(issues_count)


def record_audit_log_entry(action: str, resource_type: str):
    """Record audit log entry."""
    audit_log_entries_total.labels(
        action=action,
        resource_type=resource_type
    ).inc()


def get_metrics() -> Response:
    """Return Prometheus metrics."""
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


# OpenTelemetry Setup
def setup_telemetry(service_name: str = "mtbf-api"):
    """Setup OpenTelemetry tracing and metrics."""
    # Setup Tracing
    trace.set_tracer_provider(TracerProvider())
    tracer = trace.get_tracer(__name__)
    
    # Setup Metrics with Prometheus exporter
    from opentelemetry.exporter.prometheus import PrometheusMetricReader
    from opentelemetry.sdk.metrics import MeterProvider
    
    metric_reader = PrometheusMetricReader()
    set_meter_provider(MeterProvider(metric_readers=[metric_reader]))
    
    return tracer


def create_middleware():
    """Create FastAPI middleware for metrics collection."""
    from fastapi import Request
    from starlette.middleware.base import BaseHTTPMiddleware
    
    class MetricsMiddleware(BaseHTTPMiddleware):
        async def dispatch(self, request: Request, call_next):
            start_time = time.time()
            
            response = await call_next(request)
            
            duration = time.time() - start_time
            
            # Record metrics
            record_api_request(
                method=request.method,
                endpoint=request.url.path,
                status_code=response.status_code,
                duration=duration
            )
            
            return response
    
    return MetricsMiddleware


# Tracing decorator
def trace_operation(operation_name: str):
    """Decorator to trace operations."""
    def decorator(func):
        def wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            with tracer.start_as_current_span(operation_name) as span:
                span.set_attribute("operation.name", operation_name)
                try:
                    result = func(*args, **kwargs)
                    span.set_attribute("operation.success", True)
                    return result
                except Exception as e:
                    span.set_attribute("operation.success", False)
                    span.set_attribute("operation.error", str(e))
                    span.record_exception(e)
                    raise
        return wrapper
    return decorator