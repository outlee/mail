import pytest
from app.models.asset import Asset, AssetGroup, AssetGroupMember
from app.models.failure import FailureEvent, FailureEventUpdate
from app.models.kpi import KPISnapshot
from app.models.monitoring import AssetRuntimeCounter
from app.models.auth import User, Role, UserRole
from app.models.alert import AlertPolicy, AlertOccurrence
from app.models.import_job import CSVImportJob
from app.models.audit import AuditLogEntry


def test_model_relationships():
    """Test that model relationships are properly defined."""
    # Test Asset relationships
    assert hasattr(Asset, 'runtime_counters'), "Asset should have runtime_counters relationship"
    assert hasattr(Asset, 'failure_events'), "Asset should have failure_events relationship"
    assert hasattr(Asset, 'kpi_snapshots'), "Asset should have kpi_snapshots relationship"
    assert hasattr(Asset, 'group_memberships'), "Asset should have group_memberships relationship"
    
    # Test FailureEvent relationships
    assert hasattr(FailureEvent, 'asset'), "FailureEvent should have asset relationship"
    assert hasattr(FailureEvent, 'updates'), "FailureEvent should have updates relationship"
    
    # Test AssetRuntimeCounter relationships
    assert hasattr(AssetRuntimeCounter, 'asset'), "AssetRuntimeCounter should have asset relationship"
    
    # Test KPISnapshot relationships
    assert hasattr(KPISnapshot, 'asset'), "KPISnapshot should have asset relationship"
    
    # Test User relationships
    assert hasattr(User, 'user_roles'), "User should have user_roles relationship"
    
    # Test Role relationships
    assert hasattr(Role, 'users'), "Role should have users relationship"
    
    # Test UserRole relationships
    assert hasattr(UserRole, 'user'), "UserRole should have user relationship"
    assert hasattr(UserRole, 'role'), "UserRole should have role relationship"
    
    # Test AlertPolicy relationships
    assert hasattr(AlertPolicy, 'occurrences'), "AlertPolicy should have occurrences relationship"
    
    # Test AlertOccurrence relationships
    assert hasattr(AlertOccurrence, 'policy'), "AlertOccurrence should have policy relationship"
    
    # Test AssetGroup relationships
    assert hasattr(AssetGroup, 'members'), "AssetGroup should have members relationship"
    
    # Test AssetGroupMember relationships
    assert hasattr(AssetGroupMember, 'asset'), "AssetGroupMember should have asset relationship"
    assert hasattr(AssetGroupMember, 'group'), "AssetGroupMember should have group relationship"
    
    # Test FailureEventUpdate relationships
    assert hasattr(FailureEventUpdate, 'failure_event'), "FailureEventUpdate should have failure_event relationship"


def test_model_enums():
    """Test that model enums are properly defined."""
    from app.models.asset import AssetStatus, AssetType
    from app.models.failure import FailureSeverity, FailureMode, FailureStatus
    from app.models.kpi import KPIType
    from app.models.monitoring import CounterType
    from app.models.auth import UserStatus
    from app.models.alert import AlertSeverity, AlertStatus, EvaluationFrequency
    from app.models.import_job import ImportStatus, ImportType
    from app.models.audit import AuditAction
    
    # Test Asset enums
    assert hasattr(AssetStatus, 'ACTIVE')
    assert hasattr(AssetStatus, 'INACTIVE')
    assert hasattr(AssetType, 'MACHINERY')
    assert hasattr(AssetType, 'OTHER')
    
    # Test Failure enums
    assert hasattr(FailureSeverity, 'LOW')
    assert hasattr(FailureSeverity, 'CRITICAL')
    assert hasattr(FailureMode, 'MECHANICAL')
    assert hasattr(FailureMode, 'OTHER')
    assert hasattr(FailureStatus, 'OPEN')
    assert hasattr(FailureStatus, 'RESOLVED')
    
    # Test KPI enums
    assert hasattr(KPIType, 'MTBF')
    assert hasattr(KPIType, 'MTTR')
    assert hasattr(KPIType, 'AVAILABILITY')
    
    # Test Monitoring enums
    assert hasattr(CounterType, 'OPERATING_HOURS')
    assert hasattr(CounterType, 'PRODUCTION_CYCLES')
    
    # Test Auth enums
    assert hasattr(UserStatus, 'ACTIVE')
    assert hasattr(UserStatus, 'PENDING')
    
    # Test Alert enums
    assert hasattr(AlertSeverity, 'WARNING')
    assert hasattr(AlertSeverity, 'CRITICAL')
    assert hasattr(AlertStatus, 'ACTIVE')
    assert hasattr(EvaluationFrequency, 'HOURLY')
    
    # Test Import enums
    assert hasattr(ImportStatus, 'PENDING')
    assert hasattr(ImportStatus, 'COMPLETED')
    assert hasattr(ImportType, 'ASSETS')
    
    # Test Audit enums
    assert hasattr(AuditAction, 'CREATE')
    assert hasattr(AuditAction, 'UPDATE')
    assert hasattr(AuditAction, 'DELETE')


def test_model_table_names():
    """Test that model table names are properly defined."""
    assert Asset.__tablename__ == "assets"
    assert AssetGroup.__tablename__ == "asset_groups"
    assert AssetGroupMember.__tablename__ == "asset_group_members"
    assert FailureEvent.__tablename__ == "failure_events"
    assert FailureEventUpdate.__tablename__ == "failure_event_updates"
    assert KPISnapshot.__tablename__ == "kpi_snapshots"
    assert AssetRuntimeCounter.__tablename__ == "asset_runtime_counters"
    assert User.__tablename__ == "users"
    assert Role.__tablename__ == "roles"
    assert UserRole.__tablename__ == "user_roles"
    assert AlertPolicy.__tablename__ == "alert_policies"
    assert AlertOccurrence.__tablename__ == "alert_occurrences"
    assert CSVImportJob.__tablename__ == "csv_import_jobs"
    assert AuditLogEntry.__tablename__ == "audit_log_entries"


def test_schema_imports():
    """Test that all schemas can be imported successfully."""
    try:
        from app.schemas.asset import AssetCreate, AssetUpdate, AssetRead
        from app.schemas.auth import UserCreate, UserUpdate, UserRead, RoleCreate, RoleUpdate, RoleRead
        from app.schemas.failure import FailureEventCreate, FailureEventUpdate, FailureEventRead
        from app.schemas.kpi import KPISnapshotCreate, KPISnapshotUpdate, KPISnapshotRead
        from app.schemas.monitoring import AssetRuntimeCounterCreate, AssetRuntimeCounterUpdate, AssetRuntimeCounterRead
        from app.schemas.alert import AlertPolicyCreate, AlertPolicyUpdate, AlertPolicyRead, AlertOccurrenceCreate, AlertOccurrenceUpdate, AlertOccurrenceRead
        from app.schemas.import_job import CSVImportJobCreate, CSVImportJobUpdate, CSVImportJobRead
        from app.schemas.audit import AuditLogEntryCreate, AuditLogEntryRead
    except ImportError as e:
        pytest.fail(f"Failed to import schemas: {e}")


def test_alembic_migration_exists():
    """Test that Alembic migration file exists."""
    import os
    migration_dir = "/home/engine/project/backend/alembic/versions"
    assert os.path.exists(migration_dir), "Alembic versions directory should exist"
    
    migration_files = [f for f in os.listdir(migration_dir) if f.endswith('.py')]
    assert len(migration_files) > 0, "Should have at least one migration file"
    
    # Check for initial migration
    initial_migration = None
    for f in migration_files:
        if "initial" in f.lower():
            initial_migration = f
            break
    
    assert initial_migration is not None, "Should have initial migration file"
    
    # Check that migration file contains expected content
    migration_path = os.path.join(migration_dir, initial_migration)
    with open(migration_path, 'r') as file:
        content = file.read()
        assert "create_table" in content, "Migration should contain table creation commands"
        assert "roles" in content, "Migration should create roles table"
        assert "assets" in content, "Migration should create assets table"


if __name__ == "__main__":
    pytest.main([__file__])