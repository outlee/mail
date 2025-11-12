#!/usr/bin/env python3
"""
Demo data seeding script for MTBF Platform

This script populates the database with sample data for local development and demos:
- Users with different roles
- Assets and groups
- KPI snapshots with realistic values
- Task run history

Usage:
    python scripts/seed_demo.py
    
Environment variables:
    DATABASE_URL: PostgreSQL connection string (default: postgresql://postgres:postgres@localhost:5432/mtbf)
"""
import os
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "backend"))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import Base
from app.models.asset import Asset, Group
from app.models.auth import User, UserRole
from app.models.kpi import KPISnapshot
from app.models.monitoring import TaskRun, TaskRunStatus
from app.security import hash_password


def get_database_url():
    return os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost:5432/mtbf"
    )


def create_users(session):
    print("Creating users...")
    users = [
        User(
            id=str(uuid.uuid4()),
            email="admin@mtbf.local",
            hashed_password=hash_password("admin123"),
            full_name="System Administrator",
            role=UserRole.MAINTAINER,
            is_active=True,
        ),
        User(
            id=str(uuid.uuid4()),
            email="operator@mtbf.local",
            hashed_password=hash_password("operator123"),
            full_name="Operations User",
            role=UserRole.OPERATOR,
            is_active=True,
        ),
        User(
            id=str(uuid.uuid4()),
            email="manager@mtbf.local",
            hashed_password=hash_password("manager123"),
            full_name="Management User",
            role=UserRole.MANAGER,
            is_active=True,
        ),
    ]
    
    for user in users:
        existing = session.query(User).filter_by(email=user.email).first()
        if not existing:
            session.add(user)
            print(f"  Created user: {user.email} (role: {user.role.value})")
        else:
            print(f"  User already exists: {user.email}")
    
    session.commit()
    return users


def create_assets(session, count=20):
    print(f"Creating {count} assets...")
    assets = []
    
    asset_names = [
        "Production Line A", "Production Line B", "Production Line C",
        "Injection Molder 1", "Injection Molder 2", "Injection Molder 3",
        "CNC Machine 1", "CNC Machine 2", "CNC Machine 3",
        "Assembly Robot 1", "Assembly Robot 2", "Assembly Robot 3",
        "Conveyor Belt A", "Conveyor Belt B", "Conveyor Belt C",
        "Quality Control Station 1", "Quality Control Station 2",
        "Packaging Machine 1", "Packaging Machine 2", "Packaging Machine 3",
    ]
    
    for i, name in enumerate(asset_names[:count]):
        asset = Asset(
            id=str(uuid.uuid4()),
            name=name,
            description=f"Demo asset for testing and development purposes. Asset #{i+1}",
        )
        assets.append(asset)
        session.add(asset)
        print(f"  Created asset: {name}")
    
    session.commit()
    return assets


def create_groups(session, assets):
    print("Creating asset groups...")
    groups = []
    
    group_configs = [
        ("Production Lines", "All main production line assets", [0, 1, 2]),
        ("Molding Equipment", "Injection molding machines", [3, 4, 5]),
        ("CNC Equipment", "Computer numerical control machines", [6, 7, 8]),
        ("Robotics", "Assembly and handling robots", [9, 10, 11]),
        ("Material Handling", "Conveyors and transport systems", [12, 13, 14]),
        ("Quality & Packaging", "QC and packaging equipment", [15, 16, 17, 18, 19]),
    ]
    
    for name, description, asset_indices in group_configs:
        group = Group(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
        )
        groups.append(group)
        session.add(group)
        print(f"  Created group: {name} with {len(asset_indices)} assets")
    
    session.commit()
    return groups


def create_kpi_snapshots(session, assets, groups, days_back=30):
    print(f"Creating KPI snapshots for the last {days_back} days...")
    snapshots_created = 0
    
    now = datetime.utcnow()
    base_values = {
        "rolling": 95.0,
        "calendar": 92.0,
    }
    
    for asset in assets:
        for day in range(days_back):
            date = now - timedelta(days=day)
            period_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(hours=1)
            
            for kpi_type in ["rolling"]:
                import random
                base_value = base_values[kpi_type]
                variation = random.uniform(-5.0, 5.0)
                value = max(0, min(100, base_value + variation))
                
                snapshot = KPISnapshot(
                    id=str(uuid.uuid4()),
                    asset_id=asset.id,
                    kpi_type=kpi_type,
                    value=round(value, 2),
                    period_start=period_start,
                    period_end=period_end,
                )
                session.add(snapshot)
                snapshots_created += 1
    
    for group in groups:
        for day in range(days_back):
            date = now - timedelta(days=day)
            period_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
            period_end = period_start + timedelta(days=1)
            
            for kpi_type in ["calendar"]:
                import random
                base_value = base_values[kpi_type]
                variation = random.uniform(-3.0, 3.0)
                value = max(0, min(100, base_value + variation))
                
                snapshot = KPISnapshot(
                    id=str(uuid.uuid4()),
                    group_id=group.id,
                    kpi_type=kpi_type,
                    value=round(value, 2),
                    period_start=period_start,
                    period_end=period_end,
                )
                session.add(snapshot)
                snapshots_created += 1
    
    session.commit()
    print(f"  Created {snapshots_created} KPI snapshots")


def create_task_runs(session, assets, groups, count=50):
    print(f"Creating {count} task run records...")
    
    task_types = [
        ("recompute_rolling_kpis_task", "all_assets"),
        ("recompute_calendar_kpis_task", "all_groups"),
        ("recompute_rolling_kpis_task", "single_asset"),
        ("recompute_calendar_kpis_task", "single_group"),
    ]
    
    statuses = [
        (TaskRunStatus.SUCCESS, 0.85),
        (TaskRunStatus.FAILED, 0.10),
        (TaskRunStatus.RUNNING, 0.03),
        (TaskRunStatus.PENDING, 0.02),
    ]
    
    now = datetime.utcnow()
    
    for i in range(count):
        import random
        task_name, scope = random.choice(task_types)
        
        cumulative_prob = 0
        status = TaskRunStatus.SUCCESS
        for s, prob in statuses:
            cumulative_prob += prob
            if random.random() < cumulative_prob:
                status = s
                break
        
        created_at = now - timedelta(hours=random.randint(1, 240))
        started_at = created_at + timedelta(seconds=random.randint(1, 30))
        completed_at = None
        error_message = None
        items_processed = 0
        
        if status in [TaskRunStatus.SUCCESS, TaskRunStatus.FAILED]:
            completed_at = started_at + timedelta(seconds=random.randint(5, 300))
            items_processed = random.randint(1, len(assets) if "asset" in scope else len(groups))
        
        if status == TaskRunStatus.FAILED:
            error_message = random.choice([
                "Database connection timeout",
                "Resource temporarily unavailable",
                "Lock acquisition failed",
                "Invalid KPI calculation parameters",
            ])
        
        task_run = TaskRun(
            id=str(uuid.uuid4()),
            task_name=task_name,
            task_id=f"celery-task-{uuid.uuid4()}",
            status=status,
            scope=scope,
            asset_id=random.choice(assets).id if "single_asset" in scope else None,
            group_id=random.choice(groups).id if "single_group" in scope else None,
            started_at=started_at if status != TaskRunStatus.PENDING else None,
            completed_at=completed_at,
            error_message=error_message,
            items_processed=str(items_processed),
            created_at=created_at,
        )
        session.add(task_run)
    
    session.commit()
    print(f"  Created {count} task run records")


def main():
    database_url = get_database_url()
    print(f"Seeding database: {database_url}")
    print("-" * 80)
    
    engine = create_engine(database_url, echo=False)
    
    print("\nEnsuring database tables exist...")
    Base.metadata.create_all(bind=engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        users = create_users(session)
        assets = create_assets(session, count=20)
        groups = create_groups(session, assets)
        create_kpi_snapshots(session, assets, groups, days_back=30)
        create_task_runs(session, assets, groups, count=50)
        
        print("\n" + "=" * 80)
        print("✅ Database seeding completed successfully!")
        print("=" * 80)
        print("\nDemo login credentials:")
        print("  Admin:    admin@mtbf.local / admin123")
        print("  Operator: operator@mtbf.local / operator123")
        print("  Manager:  manager@mtbf.local / manager123")
        print("\nDemo data summary:")
        print(f"  Users:        {len(users)}")
        print(f"  Assets:       {len(assets)}")
        print(f"  Groups:       {len(groups)}")
        print(f"  KPI Data:     Last 30 days")
        print(f"  Task History: 50 records")
        
    except Exception as e:
        print(f"\n❌ Error during seeding: {e}")
        session.rollback()
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
