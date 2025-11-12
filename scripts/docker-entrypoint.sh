#!/bin/bash
set -e

echo "Starting MTBF Platform API..."

# Wait for database to be ready
echo "Waiting for PostgreSQL..."
while ! pg_isready -h postgres -p 5432 -U postgres > /dev/null 2>&1; do
  sleep 1
done
echo "PostgreSQL is ready!"

# Run database migrations if available
# echo "Running database migrations..."
# alembic upgrade head

# Seed database if SEED_DB environment variable is set
if [ "$SEED_DB" = "true" ]; then
  echo "Seeding database with demo data..."
  python -c "
import sys
sys.path.insert(0, '/app')
from app.database import Base, engine
from app.models import User, Asset, Group, KPISnapshot, TaskRun, UserRole, TaskRunStatus
from app.security import hash_password
import uuid
from datetime import datetime, timedelta

Base.metadata.create_all(bind=engine)

from sqlalchemy.orm import sessionmaker
Session = sessionmaker(bind=engine)
session = Session()

# Create users
users_data = [
    ('admin@mtbf.local', 'admin123', 'System Administrator', UserRole.MAINTAINER),
    ('operator@mtbf.local', 'operator123', 'Operations User', UserRole.OPERATOR),
    ('manager@mtbf.local', 'manager123', 'Management User', UserRole.MANAGER),
]

for email, password, full_name, role in users_data:
    existing = session.query(User).filter_by(email=email).first()
    if not existing:
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            hashed_password=hash_password(password),
            full_name=full_name,
            role=role,
            is_active=True,
        )
        session.add(user)
        print(f'Created user: {email}')

session.commit()
print('Database seeding completed!')
session.close()
"
fi

# Start the application
echo "Starting uvicorn..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
