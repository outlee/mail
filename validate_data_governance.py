#!/usr/bin/env python3
"""
Data Governance Validation Script

This script validates that the data governance implementation meets the requirements.
"""

import sys
import os
from pathlib import Path

# Add backend to path for imports
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path))

def validate_models():
    """Validate that all required models are defined."""
    print("🔍 Validating data models...")
    
    try:
        from app.models import (
            AssetRuntime, FailureEvent, AuditLogEntry, DataQualityReport,
            Asset, Group, KPISnapshot, TaskRun, User, RefreshToken
        )
        print("✅ All models imported successfully")
        
        # Check model attributes
        required_fields = {
            'AssetRuntime': ['asset_id', 'runtime_counter', 'recorded_at'],
            'FailureEvent': ['asset_id', 'severity', 'start_time', 'end_time', 'description'],
            'AuditLogEntry': ['user_id', 'action', 'resource_type', 'resource_id', 'old_values', 'new_values'],
            'DataQualityReport': ['report_type', 'status', 'issues_found', 'assets_checked']
        }
        
        for model_name, fields in required_fields.items():
            model_class = locals()[model_name]
            for field in fields:
                if not hasattr(model_class, field):
                    print(f"❌ {model_name} missing field: {field}")
                    return False
                else:
                    print(f"✅ {model_name}.{field} exists")
        
        return True
        
    except ImportError as e:
        print(f"❌ Model import failed: {e}")
        return False


def validate_services():
    """Validate that all required services are defined."""
    print("\n🔍 Validating services...")
    
    try:
        from app.services import (
            AssetRuntimeService, FailureEventService, AuditLogService, DataQualityService
        )
        print("✅ All services imported successfully")
        
        # Check service methods
        required_methods = {
            'AssetRuntimeService': ['create_asset_runtime', 'get_asset_runtime_by_id', 'list_asset_runtimes'],
            'FailureEventService': ['create_failure_event', 'get_failure_event_by_id', 'update_failure_event', 'delete_failure_event'],
            'AuditLogService': ['create_audit_entry', 'list_audit_entries'],
            'DataQualityService': ['run_data_quality_check', 'create_data_quality_report', 'list_data_quality_reports']
        }
        
        for service_name, methods in required_methods.items():
            service_class = locals()[service_name]
            for method in methods:
                if not hasattr(service_class, method):
                    print(f"❌ {service_name} missing method: {method}")
                    return False
                else:
                    print(f"✅ {service_name}.{method} exists")
        
        return True
        
    except ImportError as e:
        print(f"❌ Service import failed: {e}")
        return False


def validate_schemas():
    """Validate that all required schemas are defined."""
    print("\n🔍 Validating schemas...")
    
    try:
        from app.schemas import (
            AssetRuntimeCreate, AssetRuntimeResponse,
            FailureEventCreate, FailureEventUpdate, FailureEventResponse,
            AuditLogEntryResponse, DataQualityReportResponse, DataQualityRequest
        )
        print("✅ All schemas imported successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Schema import failed: {e}")
        return False


def validate_routes():
    """Validate that all required routes are defined."""
    print("\n🔍 Validating routes...")
    
    try:
        from app.routes import (
            asset_runtime_router, failure_events_router, audit_router, data_quality_router
        )
        print("✅ All routers imported successfully")
        
        # Check router routes
        routers = {
            'asset_runtime_router': asset_runtime_router,
            'failure_events_router': failure_events_router,
            'audit_router': audit_router,
            'data_quality_router': data_quality_router
        }
        
        for router_name, router in routers.items():
            route_count = len(router.routes)
            print(f"✅ {router_name} has {route_count} routes")
        
        return True
        
    except ImportError as e:
        print(f"❌ Route import failed: {e}")
        return False


def validate_metrics():
    """Validate that metrics module is properly configured."""
    print("\n🔍 Validating metrics...")
    
    try:
        from app.metrics import (
            record_api_request, record_validation_failure, record_task_execution,
            record_data_quality_issues, record_audit_log_entry, get_metrics
        )
        print("✅ All metrics functions imported successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Metrics import failed: {e}")
        return False


def validate_worker_tasks():
    """Validate that worker tasks are defined."""
    print("\n🔍 Validating worker tasks...")
    
    try:
        # Add worker to path
        worker_path = Path(__file__).parent / "worker"
        sys.path.insert(0, str(worker_path))
        
        from worker.tasks import data_quality_check_task
        print("✅ Data quality check task imported successfully")
        return True
        
    except ImportError as e:
        print(f"❌ Worker task import failed: {e}")
        return False


def validate_monitoring():
    """Validate monitoring configuration."""
    print("\n🔍 Validating monitoring setup...")
    
    # Check for monitoring directory
    monitoring_dir = Path(__file__).parent / "monitoring"
    if not monitoring_dir.exists():
        print("❌ Monitoring directory not found")
        return False
    
    prometheus_config = monitoring_dir / "prometheus.yml"
    if not prometheus_config.exists():
        print("❌ Prometheus configuration not found")
        return False
    
    grafana_config = monitoring_dir / "grafana"
    if not grafana_config.exists():
        print("❌ Grafana configuration not found")
        return False
    
    print("✅ Monitoring configuration files exist")
    return True


def validate_docker_compose():
    """Validate Docker Compose configuration."""
    print("\n🔍 Validating Docker Compose...")
    
    docker_compose_path = Path(__file__).parent / "docker-compose.yml"
    if not docker_compose_path.exists():
        print("❌ docker-compose.yml not found")
        return False
    
    with open(docker_compose_path) as f:
        content = f.read()
        
        if 'prometheus:' not in content:
            print("❌ Prometheus service not found in docker-compose.yml")
            return False
        
        if 'grafana:' not in content:
            print("❌ Grafana service not found in docker-compose.yml")
            return False
        
        print("✅ Docker Compose has monitoring services")
        return True


def main():
    """Run all validations."""
    print("🚀 Data Governance Validation\n")
    
    validations = [
        validate_models,
        validate_services,
        validate_schemas,
        validate_routes,
        validate_metrics,
        validate_worker_tasks,
        validate_monitoring,
        validate_docker_compose
    ]
    
    passed = 0
    total = len(validations)
    
    for validation in validations:
        if validation():
            passed += 1
        else:
            print("❌ Validation failed")
    
    print(f"\n📊 Results: {passed}/{total} validations passed")
    
    if passed == total:
        print("🎉 All data governance validations passed!")
        return 0
    else:
        print("💥 Some validations failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())