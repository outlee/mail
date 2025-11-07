# MTBF Platform

A modern full-stack platform built with FastAPI, Celery, React, and Docker.

## 🏗️ Architecture

This project uses a monorepo structure with the following components:

- **Backend** (`backend/`): FastAPI application with SQLAlchemy ORM
- **Worker** (`worker/`): Celery workers for asynchronous task processing
- **Frontend** (`frontend/`): React + Vite + TypeScript + Ant Design
- **Infrastructure** (`infrastructure/`): Docker and deployment configurations

## ✨ Key Features

### 🚨 Alerting System
- **Policy Management**: Create and manage alert policies with customizable thresholds
- **Multi-Channel Notifications**: Email and webhook notifications with deduplication
- **Real-time Evaluation**: Automatic alert evaluation after KPI computation
- **Audit Trail**: Complete alert lifecycle tracking and event logging
- **Role-Based Access**: Granular permissions for alert management

### 📊 KPI Monitoring
- **Automated Scheduling**: Hourly rolling and daily calendar KPI computation
- **Asset & Group Tracking**: Monitor individual assets and aggregated groups
- **Advisory Locking**: Prevent concurrent computation conflicts
- **Task Tracking**: Complete audit trail of KPI computations

### 🔐 Authentication & Authorization
- **JWT-Based Auth**: Secure access and refresh token rotation
- **Role-Based Control**: Maintainer, Operator, and Manager roles
- **Protected Routes**: API endpoint security with role validation
- **Session Management**: Secure token storage and automatic refresh

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

### Backend Tests

```bash
# Run all tests
make test

# Run specific test file
cd backend
pytest tests/test_health.py

# Run with coverage
pytest --cov=app --cov-report=html
```

### Frontend Tests

```bash
cd frontend
npm run test  # Add test script when test suite is implemented
```

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

## 📚 Documentation

- **[SCHEDULING.md](./SCHEDULING.md)** - KPI scheduling system documentation
- **[AUTH.md](./AUTH.md)** - Authentication system documentation  
- **[ALERTING.md](./ALERTING.md)** - Alerting system documentation
- **[SETUP.md](./SETUP.md)** - Development setup guide
- **[VERIFICATION.md](./VERIFICATION.md)** - System verification guide

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
