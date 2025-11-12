# MTBF Platform

[![CI Pipeline](https://github.com/your-username/mtbf-platform/actions/workflows/ci.yml/badge.svg)](https://github.com/your-username/mtbf-platform/actions/workflows/ci.yml)

A modern full-stack platform built with FastAPI, Celery, React, and Docker.

## 🏗️ Architecture

This project uses a monorepo structure with the following components:

- **Backend** (`backend/`): FastAPI application with SQLAlchemy ORM
- **Worker** (`worker/`): Celery workers for asynchronous task processing
- **Frontend** (`frontend/`): React + Vite + TypeScript + Ant Design
- **Infrastructure** (`infrastructure/`): Docker and deployment configurations

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ (for local frontend development)
- Python 3.11+ (for local backend development)

### Running with Docker

1. Clone the repository and navigate to the project directory:

```bash
git clone <repository-url>
cd mtbf-platform
```

2. Copy the environment file:

```bash
cp .env.example .env
```

3. Build and start all services:

```bash
docker compose up --build
```

4. Access the services:

- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs
- **Health Check**: http://localhost:8000/health

### Using Make Commands

The project includes a Makefile with helpful commands:

```bash
make help          # Show all available commands
make build         # Build all Docker containers
make up            # Start all services
make down          # Stop all services
make logs          # View logs from all services
make restart       # Restart all services
make clean         # Remove all containers and volumes
make test          # Run backend tests
make lint          # Run linters
make format        # Format code
make install       # Install dependencies locally
```

## 📦 Services

### API Service

- **Port**: 8000
- **Technology**: FastAPI + SQLAlchemy
- **Database**: PostgreSQL
- **Features**:
  - RESTful API endpoints
  - Health check endpoint
  - SQLAlchemy ORM integration
  - Pydantic settings management
  - Structured logging

#### CSV Import API

The API exposes CSV ingestion endpoints that validate payloads, persist raw files, and process records via Celery workers.

| Endpoint | HTTP Method | Description | Required Header | Required Columns |
|----------|-------------|-------------|-----------------|------------------|
| `/api/v1/imports/assets`   | `POST` | Upload asset definitions | `X-Idempotency-Key` | `external_id`, `name` |
| `/api/v1/imports/runtime`  | `POST` | Upload runtime counters | `X-Idempotency-Key` | `asset_external_id`, `counter_name`, `value`, `recorded_at` |
| `/api/v1/imports/failures` | `POST` | Upload failure events | `X-Idempotency-Key` | `asset_external_id`, `failure_code`, `occurred_at` |
| `/api/v1/imports/{job_id}` | `GET`  | Retrieve job status | Bearer token | _n/a_ |

Key behaviours:

- Files must be uploaded with `Content-Type: text/csv` and are limited to `5 MiB` (configurable via `CSV_IMPORT_MAX_BYTES`).
- Requests without `X-Idempotency-Key` or with duplicate keys inside the TTL window (`CSV_IMPORT_IDEMPOTENCY_TTL_MINUTES`, default 60 minutes) return the previously created job without re-processing.
- Successful uploads create a `csv_import_jobs` record and enqueue `worker.tasks.process_csv_import_task` for background processing.
- Job status responses include total, processed, skipped, and errored row counts plus a sample of row-level validation errors.

Sample payloads:

<details>
<summary>Assets CSV</summary>

```csv
external_id,name,description
asset-001,Main Generator,Primary power supply
asset-002,Backup Generator,Secondary power supply
```
</details>

<details>
<summary>Runtime Counters CSV</summary>

```csv
asset_external_id,counter_name,value,recorded_at
asset-001,uptime_hours,121.5,2023-10-01T00:00:00Z
asset-001,start_count,4,2023-10-01T12:00:00Z
```
</details>

<details>
<summary>Failure Events CSV</summary>

```csv
asset_external_id,failure_code,occurred_at,description,resolved_at
asset-001,FAIL-001,2023-10-01T02:15:00Z,Unexpected shutdown,2023-10-01T03:00:00Z
```
</details>

Use `GET /api/v1/imports/{job_id}` to poll progress. Completed jobs with partial failures surface a non-empty `error_sample` array and descriptive message while still committing valid rows.

### Worker Service

- **Technology**: Celery
- **Broker**: Redis
- **Features**:
  - Asynchronous task processing
  - Periodic tasks via Celery Beat
  - Shared configuration with API
  - Heartbeat monitoring

### Scheduler Service

- **Technology**: Celery Beat
- **Features**:
  - Periodic task scheduling
  - Cron-based task execution

### Web Service

- **Port**: 5173 (development), 80 (production)
- **Technology**: React + Vite + TypeScript
- **UI Library**: Ant Design
- **Features**:
  - Modern React hooks-based architecture
  - TypeScript for type safety
  - Ant Design component library
  - API client with Axios
  - React Router for navigation

### PostgreSQL

- **Port**: 5432
- **Database**: mtbf
- **User**: postgres (configurable)

### Redis

- **Port**: 6379
- **Purpose**: Celery broker and result backend

## 🛠️ Development

### Backend Development

#### Local Setup

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements-dev.txt
```

#### Running Tests

```bash
cd backend
pytest
```

#### Code Quality

```bash
# Linting
ruff check .

# Formatting
black .
isort .
```

#### Database Migrations

```bash
# Create a new migration
make migration

# Apply migrations
make migrate
```

### Frontend Development

#### Local Setup

```bash
cd frontend
npm install
```

#### Running Development Server

```bash
npm run dev
```

#### Code Quality

```bash
# Linting
npm run lint

# Formatting
npm run format
```

#### Building for Production

```bash
npm run build
```

### Worker Development

The worker shares configuration with the backend and uses the same Docker network.

```bash
# View worker logs
docker compose logs -f worker

# View scheduler logs
docker compose logs -f scheduler

# Access worker shell
make worker-shell
```

## 🔧 Configuration

### Environment Variables

All configuration is managed through environment variables. Copy `.env.example` to `.env` and adjust as needed:

#### Database Configuration

- `POSTGRES_USER`: PostgreSQL username (default: postgres)
- `POSTGRES_PASSWORD`: PostgreSQL password (default: postgres)
- `POSTGRES_DB`: Database name (default: mtbf)
- `DATABASE_URL`: Full database connection string

#### Redis Configuration

- `REDIS_URL`: Redis connection string (default: redis://redis:6379/0)

#### Celery Configuration

- `CELERY_BROKER_URL`: Celery broker URL (default: redis://redis:6379/0)
- `CELERY_RESULT_BACKEND`: Celery result backend URL (default: redis://redis:6379/0)

#### Application Configuration

- `DEBUG`: Enable debug mode (default: false)
- `ENVIRONMENT`: Environment name (default: development)

#### Frontend Configuration

- `VITE_API_URL`: Backend API URL (default: http://localhost:8000)

## 📊 Service Ports

| Service    | Port | Description                    |
|------------|------|--------------------------------|
| Frontend   | 5173 | React development server       |
| Backend    | 8000 | FastAPI application            |
| PostgreSQL | 5432 | Database server                |
| Redis      | 6379 | Cache and message broker       |

## 🧪 Testing

The MTBF Platform includes comprehensive automated testing with pytest (backend) and Playwright (frontend E2E).

### Quick Start

```bash
# Run all backend tests with coverage (requires ≥80%)
make test

# Run frontend E2E tests
make test-e2e

# Run all tests (backend + E2E)
make test-all
```

### Backend Tests

```bash
# Run all tests with coverage
cd backend
pytest

# Run specific test file
pytest tests/test_services.py

# Run specific test
pytest tests/test_services.py::TestAssetService::test_create_asset

# Generate HTML coverage report
pytest --cov=app --cov-report=html
```

**Coverage Requirements:**
- Minimum: 80% (enforced)
- Reports: `reports/coverage/backend/`

### Frontend E2E Tests

```bash
# Run all E2E tests (headless)
cd frontend
npm run test:e2e

# Run in debug mode
npm run test:e2e:debug

# View test report
npx playwright show-report ../reports/playwright
```

**Test Coverage:**
- Authentication flows (login, logout, validation)
- Dashboard navigation and responsiveness
- Alerts management (create, view, acknowledge)
- Role-based access control

### Worker Tests

```bash
cd worker
pytest  # Run worker tests with coverage
```

### Test Reports

All test reports are stored in `reports/`:

```
reports/
├── coverage/
│   └── backend/        # HTML coverage reports
├── junit/
│   ├── backend-results.xml
│   └── e2e-results.xml
└── playwright/         # E2E test reports with screenshots/videos
```

### Demo Data Seeding

Populate the database with sample data for testing and demos:

```bash
# Seed with demo data
make seed

# Or run directly
python scripts/seed_demo.py
```

**Demo Credentials:**
- Admin: `admin@mtbf.local` / `admin123`
- Operator: `operator@mtbf.local` / `operator123`
- Manager: `manager@mtbf.local` / `manager123`

## 🔄 Continuous Integration

This project uses GitHub Actions for continuous integration. The CI pipeline runs on every push and pull request to the `main` and `develop` branches.

### CI Workflow Jobs

1. **Backend Tests**: Runs linting (ruff, black, isort) and pytest with PostgreSQL and Redis services
2. **Frontend Tests**: Runs ESLint, TypeScript compilation, and Playwright E2E tests
3. **Worker Tests**: Runs linting and pytest for Celery worker tasks
4. **Integration Tests**: Builds and runs the full Docker stack with smoke tests

### Running CI Steps Locally

You can run the same checks locally before pushing:

```bash
# Run all linting and formatting
make lint
make format

# Run all tests
make test

# Run frontend E2E tests
cd frontend
npm install
npx playwright install
npm run test:e2e

# Run worker tests
cd worker
pytest

# Run full integration test with Docker
docker compose up --build
# Wait for services to be healthy, then run smoke tests:
curl -f http://localhost:8000/health
curl -f http://localhost:5173
docker compose exec worker celery -A worker.celery_app inspect ping
docker compose down -v
```

### CI Configuration Validation

The project includes a validation script to ensure all CI configuration files are properly set up:

```bash
./validate-ci.sh
```

This script checks:
- Required CI configuration files exist
- Makefile targets are properly defined
- Frontend package.json scripts are available
- Python project configurations are valid

### Local CI Simulation

For quick validation without running the full Docker stack, use the local CI simulation script:

```bash
./test-ci-local.sh
```

This script runs linting, formatting checks, and tests for all components locally, providing fast feedback before pushing changes.

### Using `act` for Local CI Testing

For testing the GitHub Actions workflow locally, you can use [act](https://github.com/nektos/act):

```bash
# Install act (macOS)
brew install act

# Run the full CI workflow locally
act

# Run specific job
act -j backend
```

### CI Artifacts

The CI pipeline generates the following artifacts:

- **Coverage Reports**: HTML coverage reports for backend, frontend, and worker
- **Playwright Reports**: Test execution reports and traces for E2E tests
- **Integration Logs**: Docker compose logs when integration tests fail

These artifacts are available for download from the GitHub Actions run page.

## 🐛 Troubleshooting

### Services Not Starting

1. Check Docker is running:
   ```bash
   docker ps
   ```

2. Check service logs:
   ```bash
   make logs
   ```

3. Rebuild containers:
   ```bash
   make clean
   make build
   make up
   ```

### Database Connection Issues

1. Verify PostgreSQL is healthy:
   ```bash
   docker compose ps postgres
   ```

2. Check database logs:
   ```bash
   docker compose logs postgres
   ```

3. Connect to database directly:
   ```bash
   make db-shell
   ```

### Worker Not Processing Tasks

1. Check Redis connection:
   ```bash
   make redis-cli
   ping
   ```

2. Verify worker is running:
   ```bash
   docker compose ps worker
   docker compose logs worker
   ```

3. Check Celery task queue:
   ```bash
   docker compose exec worker celery -A worker.celery_app inspect active
   ```

### Frontend Not Loading

1. Check API connectivity:
   ```bash
   curl http://localhost:8000/health
   ```

2. Verify environment variables:
   ```bash
   cat frontend/.env
   ```

3. Clear node modules and reinstall:
   ```bash
   cd frontend
   rm -rf node_modules
   npm install
   ```

## 📝 Project Structure

```
.
├── backend/                 # FastAPI backend
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py         # FastAPI app entry point
│   │   ├── config.py       # Settings management
│   │   ├── database.py     # Database setup
│   │   └── logging_config.py
│   ├── tests/              # Backend tests
│   ├── requirements.txt
│   └── Dockerfile
├── worker/                 # Celery workers
│   ├── worker/
│   │   ├── __init__.py
│   │   ├── celery_app.py  # Celery configuration
│   │   ├── tasks.py       # Task definitions
│   │   └── config.py
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/               # React frontend
│   ├── src/
│   │   ├── components/    # Reusable components
│   │   ├── pages/         # Page components
│   │   ├── services/      # API clients
│   │   ├── App.tsx
│   │   └── main.tsx
│   ├── package.json
│   └── Dockerfile
├── infrastructure/         # Deployment configs
├── docker-compose.yml     # Docker orchestration
├── Makefile               # Development commands
├── .env.example          # Environment template
└── README.md             # This file
```

## 🔐 Security Notes

- Never commit `.env` files to version control
- Change default passwords in production
- Use secrets management for production deployments
- Enable HTTPS in production
- Implement proper authentication and authorization

## 🚢 Deployment

### Production Considerations

1. **Environment Variables**: Use proper secrets management
2. **Database**: Use managed PostgreSQL service
3. **Redis**: Use managed Redis service
4. **Scaling**: Use Kubernetes or similar orchestration
5. **Monitoring**: Implement logging and monitoring
6. **Backups**: Set up automated database backups

### Future Extensions

- Add production-grade deployment descriptors (Kubernetes/Helm)
- Introduce Terraform for infrastructure as code
- Implement comprehensive monitoring and alerting
- Add CI/CD pipelines
- Implement authentication and authorization
- Add API rate limiting
- Implement comprehensive logging

## 📄 License

[Add your license information here]

## 🤝 Contributing

[Add contribution guidelines here]

## 📧 Contact

[Add contact information here]
