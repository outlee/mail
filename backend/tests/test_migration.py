import pytest
import tempfile
import uuid
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models import *  # noqa: F401,F403


@pytest.fixture(scope="function")
def test_db():
    """Create a temporary database for testing."""
    # Create a temporary SQLite database
    db_fd, db_path = tempfile.mkstemp()
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = SessionLocal()
    
    yield session
    
    # Cleanup
    session.close()
    engine.dispose()
    import os
    os.close(db_fd)
    os.unlink(db_path)


def test_database_creation(test_db):
    """Test that all tables are created correctly."""
    # Test that roles table exists and has default data
    result = test_db.execute(text("SELECT COUNT(*) FROM roles"))
    role_count = result.scalar()
    assert role_count == 3, f"Expected 3 default roles, got {role_count}"
    
    # Test that default role names exist
    result = test_db.execute(text("SELECT name FROM roles WHERE is_system_role = true ORDER BY name"))
    role_names = [row[0] for row in result.fetchall()]
    expected_roles = ['maintainer', 'manager', 'operator']
    assert role_names == expected_roles, f"Expected {expected_roles}, got {role_names}"
    
    # Test that all required tables exist
    tables = test_db.execute(text("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """)).fetchall()
    table_names = [table[0] for table in tables]
    
    expected_tables = [
        'alert_occurrences',
        'alert_policies', 
        'asset_group_members',
        'asset_groups',
        'asset_runtime_counters',
        'assets',
        'audit_log_entries',
        'csv_import_jobs',
        'failure_event_updates',
        'failure_events',
        'kpi_snapshots',
        'roles',
        'user_roles',
        'users'
    ]
    
    assert len(table_names) == len(expected_tables), f"Expected {len(expected_tables)} tables, got {len(table_names)}"
    
    for table in expected_tables:
        assert table in table_names, f"Table {table} not found in database"


def test_constraints_and_indexes(test_db):
    """Test that constraints and indexes are properly created."""
    # Test unique constraint on roles.name
    with pytest.raises(Exception):  # Should raise an exception for duplicate name
        test_db.execute(text("""
            INSERT INTO roles (id, name, display_name, is_system_role, is_active, created_at, updated_at)
            VALUES (:id, 'maintainer', 'Duplicate', false, true, datetime('now'), datetime('now'))
        """), {"id": uuid.uuid4()})
    
    # Test that foreign key relationships work
    # Create a tenant
    tenant_id = uuid.uuid4()
    asset_id = uuid.uuid4()
    
    # This should fail because asset doesn't exist
    with pytest.raises(Exception):
        test_db.execute(text("""
            INSERT INTO asset_runtime_counters 
            (id, asset_id, counter_type, counter_name, current_value, unit_of_measure, created_at, updated_at)
            VALUES (:id, :asset_id, 'operating_hours', 'Test Counter', 100.0, 'hours', datetime('now'), datetime('now'))
        """), {"id": uuid.uuid4(), "asset_id": asset_id})


def test_default_role_permissions(test_db):
    """Test that default roles have correct permissions."""
    # Test maintainer role permissions
    result = test_db.execute(text("""
        SELECT permissions FROM roles WHERE name = 'maintainer'
    """)).fetchone()
    
    maintainer_permissions = result[0]
    assert isinstance(maintainer_permissions, dict), "Maintainer permissions should be a dictionary"
    assert 'assets' in maintainer_permissions, "Maintainer should have asset permissions"
    assert set(maintainer_permissions['assets']) == {'read', 'update', 'create'}, "Maintainer asset permissions incorrect"
    
    # Test manager role permissions (should have all permissions)
    result = test_db.execute(text("""
        SELECT permissions FROM roles WHERE name = 'manager'
    """)).fetchone()
    
    manager_permissions = result[0]
    assert isinstance(manager_permissions, dict), "Manager permissions should be a dictionary"
    assert 'users' in manager_permissions, "Manager should have user permissions"
    assert 'delete' in manager_permissions['assets'], "Manager should have delete permissions on assets"


def test_uuid_primary_keys(test_db):
    """Test that all tables use UUID primary keys."""
    tables_with_uuid_pks = [
        'roles', 'users', 'user_roles', 'assets', 'asset_groups', 'asset_group_members',
        'asset_runtime_counters', 'failure_events', 'failure_event_updates', 'kpi_snapshots',
        'alert_policies', 'alert_occurrences', 'csv_import_jobs', 'audit_log_entries'
    ]
    
    for table_name in tables_with_uuid_pks:
        result = test_db.execute(text(f"""
            SELECT COUNT(*) FROM pragma_table_info('{table_name}') WHERE pk = 1 AND type LIKE '%uuid%'
        """)).scalar()
        assert result > 0, f"Table {table_name} should have UUID primary key"


def test_timestamp_columns(test_db):
    """Test that tables have created_at and updated_at columns."""
    tables_with_timestamps = [
        'roles', 'users', 'assets', 'asset_groups', 'asset_runtime_counters',
        'failure_events', 'failure_event_updates', 'kpi_snapshots',
        'alert_policies', 'alert_occurrences', 'csv_import_jobs', 'audit_log_entries'
    ]
    
    for table_name in tables_with_timestamps:
        # Check created_at column
        result = test_db.execute(text(f"""
            SELECT COUNT(*) FROM pragma_table_info('{table_name}') WHERE name = 'created_at'
        """)).scalar()
        assert result > 0, f"Table {table_name} should have created_at column"
        
        # Check updated_at column
        result = test_db.execute(text(f"""
            SELECT COUNT(*) FROM pragma_table_info('{table_name}') WHERE name = 'updated_at'
        """)).scalar()
        assert result > 0, f"Table {table_name} should have updated_at column"


if __name__ == "__main__":
    pytest.main([__file__])