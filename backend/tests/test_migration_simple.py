import pytest
import tempfile
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import all models to ensure they are registered with Base
from app.models.base import Base


@pytest.fixture(scope="function")
def test_db():
    """Create a temporary database for testing."""
    # Create a temporary SQLite database
    db_fd, db_path = tempfile.mkstemp()
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    
    # Create all tables (this will test the models)
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


def test_table_creation(test_db):
    """Test that all tables are created successfully."""
    # Get all table names
    result = test_db.execute(text("""
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
    """))
    table_names = [row[0] for row in result.fetchall()]
    
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


def test_required_columns_exist(test_db):
    """Test that required columns exist in key tables."""
    # Test assets table has key columns
    result = test_db.execute(text("""
        SELECT name FROM pragma_table_info('assets')
    """))
    asset_columns = [row[0] for row in result.fetchall()]
    
    required_asset_columns = ['id', 'created_at', 'updated_at', 'tenant_id', 'asset_identifier', 'name', 'status']
    for col in required_asset_columns:
        assert col in asset_columns, f"Column {col} not found in assets table"
    
    # Test failure_events table has key columns
    result = test_db.execute(text("""
        SELECT name FROM pragma_table_info('failure_events')
    """))
    failure_columns = [row[0] for row in result.fetchall()]
    
    required_failure_columns = ['id', 'created_at', 'updated_at', 'asset_id', 'severity', 'failure_mode', 'status', 'downtime_minutes']
    for col in required_failure_columns:
        assert col in failure_columns, f"Column {col} not found in failure_events table"
    
    # Test users table has key columns
    result = test_db.execute(text("""
        SELECT name FROM pragma_table_info('users')
    """))
    user_columns = [row[0] for row in result.fetchall()]
    
    required_user_columns = ['id', 'created_at', 'updated_at', 'username', 'email', 'password_hash', 'status']
    for col in required_user_columns:
        assert col in user_columns, f"Column {col} not found in users table"


def test_foreign_key_relationships(test_db):
    """Test that foreign key relationships are properly defined."""
    # Test that failure_events table has foreign key to assets
    result = test_db.execute(text("PRAGMA foreign_key_list('failure_events')"))
    fk_list = result.fetchall()
    
    asset_fk_found = False
    for fk in fk_list:
        if fk[2] == 'assets' and 'asset_id' in str(fk):
            asset_fk_found = True
            break
    
    assert asset_fk_found, "failure_events should have foreign key to assets"
    
    # Test that failure_event_updates table has foreign key to failure_events
    result = test_db.execute(text("PRAGMA foreign_key_list('failure_event_updates')"))
    fk_list = result.fetchall()
    
    update_fk_found = False
    for fk in fk_list:
        if fk[2] == 'failure_events' and 'failure_event_id' in str(fk):
            update_fk_found = True
            break
    
    assert update_fk_found, "failure_event_updates should have foreign key to failure_events"


def test_unique_constraints(test_db):
    """Test that unique constraints are properly defined."""
    # Test that users table has unique constraint on username and email
    # In SQLite, unique constraints are shown in indexes
    result = test_db.execute(text("PRAGMA index_list('users')"))
    indexes = result.fetchall()
    
    unique_indexes = [idx for idx in indexes if idx[2] == 1]  # unique=1
    
    assert len(unique_indexes) >= 2, "users table should have at least 2 unique indexes (username, email)"
    
    # Test that roles table has unique constraint on name
    result = test_db.execute(text("PRAGMA index_list('roles')"))
    indexes = result.fetchall()
    
    unique_indexes = [idx for idx in indexes if idx[2] == 1]  # unique=1
    assert len(unique_indexes) >= 1, "roles table should have unique index on name"


def test_indexes_exist(test_db):
    """Test that important indexes exist."""
    # Test that assets table has indexes on tenant_id and status
    result = test_db.execute(text("PRAGMA index_list('assets')"))
    indexes = [idx[1] for idx in result.fetchall()]  # index name
    
    # Check for tenant-related indexes
    tenant_index_found = any('tenant' in idx.lower() for idx in indexes)
    assert tenant_index_found, "assets table should have tenant-related indexes"
    
    # Test that failure_events table has indexes on occurred_at
    result = test_db.execute(text("PRAGMA index_list('failure_events')"))
    indexes = [idx[1] for idx in result.fetchall()]
    
    time_index_found = any('occurred' in idx.lower() for idx in indexes)
    assert time_index_found, "failure_events table should have index on occurred_at"


def test_model_relationships_defined():
    """Test that model relationships are properly defined."""
    from app.models.asset import Asset
    from app.models.failure import FailureEvent
    from app.models.monitoring import AssetRuntimeCounter
    
    # Test that Asset has relationships defined
    assert hasattr(Asset, 'runtime_counters'), "Asset should have runtime_counters relationship"
    assert hasattr(Asset, 'failure_events'), "Asset should have failure_events relationship"
    
    # Test that FailureEvent has asset relationship
    assert hasattr(FailureEvent, 'asset'), "FailureEvent should have asset relationship"
    
    # Test that AssetRuntimeCounter has asset relationship
    assert hasattr(AssetRuntimeCounter, 'asset'), "AssetRuntimeCounter should have asset relationship"


if __name__ == "__main__":
    pytest.main([__file__])