# MTBF Platform Setup Guide

## Project Structure Created

This monorepo contains the following components:

### Backend (FastAPI)
- **Location**: `backend/`
- **Features**:
  - FastAPI application with SQLAlchemy ORM
  - Pydantic settings management
  - Structured logging configuration
  - Health check endpoint at `/health`
  - pytest configuration with sample tests
  - Code formatting with Black and isort
  - Linting with Ruff

### Worker (Celery)
- **Location**: `worker/`
- **Features**:
  - Celery worker for asynchronous tasks
  - Redis broker and backend
  - Shared configuration with backend
  - Placeholder tasks (heartbeat, example)
  - Beat scheduler for periodic tasks

### Frontend (React + Vite)
- **Location**: `frontend/`
- **Features**:
  - React 18 with TypeScript
  - Vite for fast development
  - Ant Design UI library
  - React Router for navigation
  - Axios API client
  - ESLint and Prettier configuration

### Infrastructure
- **Location**: `infrastructure/`
- **Purpose**: Reserved for deployment configurations

## Quick Start

### 1. Environment Setup

Copy the environment file:
```bash
cp .env.example .env
```

### 2. Docker Compose

Build and start all services:
```bash
docker compose up --build
```

This will start:
- **PostgreSQL** on port 5432
- **Redis** on port 6379
- **Backend API** on port 8000
- **Celery Worker** (background)
- **Celery Beat Scheduler** (background)
- **Frontend Web** on port 5173

### 3. Verify Services

- Health Check: http://localhost:8000/health (should return `{"status":"ok"}`)
- API Docs: http://localhost:8000/docs
- Frontend: http://localhost:5173

## Development

### Backend Tests

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
pytest -v
```

### Backend Linting

```bash
cd backend
ruff check .        # Linting
black .            # Format code
isort .            # Sort imports
```

### Frontend Development

```bash
cd frontend
npm install
npm run dev        # Start dev server
npm run lint       # Lint code
npm run format     # Format code
```

## Make Commands

The project includes a Makefile for common tasks:

- `make help` - Show all commands
- `make build` - Build Docker containers
- `make up` - Start all services
- `make down` - Stop all services
- `make logs` - View logs
- `make test` - Run backend tests
- `make lint` - Lint all code
- `make format` - Format all code

## Testing Checklist

- [x] Backend health endpoint returns `{"status":"ok"}`
- [x] Backend tests pass with pytest
- [x] Backend linting passes with ruff
- [x] Frontend builds successfully
- [x] Frontend linting passes with ESLint
- [x] Docker Compose configuration created
- [x] Environment variables documented
- [x] README with comprehensive documentation
- [x] .gitignore for Python and Node.js

## Service Ports

| Service    | Port | URL                          |
|------------|------|------------------------------|
| Frontend   | 5173 | http://localhost:5173        |
| Backend    | 8000 | http://localhost:8000        |
| PostgreSQL | 5432 | postgresql://localhost:5432  |
| Redis      | 6379 | redis://localhost:6379       |

## Architecture

```
┌─────────────┐       ┌─────────────┐       ┌─────────────┐
│   Frontend  │──────>│  Backend    │──────>│  PostgreSQL │
│ React+Vite  │       │   FastAPI   │       │   Database  │
└─────────────┘       └─────────────┘       └─────────────┘
                             │
                             │
                      ┌──────┴──────┐
                      │             │
                ┌─────▼─────┐ ┌─────▼─────┐
                │   Redis   │ │  Worker   │
                │   Cache   │ │  Celery   │
                └───────────┘ └───────────┘
                                    │
                              ┌─────▼─────┐
                              │ Scheduler │
                              │   Beat    │
                              └───────────┘
```

## Next Steps

1. **Docker Build**: Due to network issues during build, Docker images need to be built when network is available
2. **Database Migrations**: Set up Alembic migrations for database schema
3. **Authentication**: Implement user authentication and authorization
4. **API Endpoints**: Add business logic endpoints
5. **Frontend Pages**: Build out additional UI pages
6. **Tests**: Expand test coverage for both backend and frontend
7. **CI/CD**: Set up GitHub Actions or similar CI/CD pipeline

## Notes

- All services use environment variables for configuration
- Backend and worker share the same configuration module
- Frontend uses environment variables prefixed with `VITE_`
- Database and Redis data persist in Docker volumes
- Development mode enables hot reloading for all services
