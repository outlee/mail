# Scripts Directory

Utility scripts for the MTBF Platform.

## Available Scripts

### seed_demo.py

Seeds the database with demo data for local development and demonstrations.

**Usage:**
```bash
# Using Make
make seed

# Direct execution
python scripts/seed_demo.py

# With custom database URL
DATABASE_URL=postgresql://user:pass@host:5432/db python scripts/seed_demo.py
```

**What it creates:**
- 3 users (admin, operator, manager) with different roles
- 20 assets with realistic names and descriptions
- 6 groups with asset associations
- 30 days of KPI snapshot history (780+ records)
- 50 task run records with various statuses

**Demo Credentials:**
- Admin: `admin@mtbf.local` / `admin123`
- Operator: `operator@mtbf.local` / `operator123`
- Manager: `manager@mtbf.local` / `manager123`

**Features:**
- Idempotent (safe to run multiple times)
- Creates database tables if they don't exist
- Skips existing users
- Generates realistic data with random variations
- Progress output during execution

**Environment Variables:**
- `DATABASE_URL`: PostgreSQL connection string (default: `postgresql://postgres:postgres@localhost:5432/mtbf`)

### docker-entrypoint.sh

Docker container entrypoint script for the API service.

**Features:**
- Waits for PostgreSQL to be ready
- Optional database seeding via `SEED_DB=true` environment variable
- Database migration support (commented, ready for Alembic)
- Starts uvicorn with hot-reload

**Usage:**
```bash
# In docker-compose.yml
environment:
  - SEED_DB=true  # Enable seeding on startup

# Or when running container manually
docker run -e SEED_DB=true mtbf-api
```

## Adding New Scripts

When adding new utility scripts:

1. Place them in this directory
2. Make them executable: `chmod +x script_name.sh`
3. Add a shebang line: `#!/usr/bin/env python3` or `#!/bin/bash`
4. Document the script in this README
5. Consider adding a Make target in the Makefile for convenience

## Best Practices

- Scripts should be idempotent (safe to run multiple times)
- Accept configuration via environment variables
- Provide helpful output and error messages
- Handle errors gracefully
- Document required dependencies
- Include usage examples
