.PHONY: help build up down logs restart clean test lint format install seed test-e2e test-all

help:
    @echo "MTBF Platform - Development Commands"
    @echo "====================================="
    @echo "make build      - Build all Docker containers"
    @echo "make up         - Start all services"
    @echo "make down       - Stop all services"
    @echo "make logs       - View logs from all services"
    @echo "make restart    - Restart all services"
    @echo "make clean      - Remove all containers, volumes, and images"
    @echo "make test       - Run backend unit/integration tests"
    @echo "make test-e2e   - Run frontend E2E tests"
    @echo "make test-all   - Run all tests (backend + E2E)"
    @echo "make lint       - Run linters for backend and frontend"
    @echo "make format     - Format code (backend and frontend)"
    @echo "make install    - Install dependencies"
    @echo "make seed       - Seed database with demo data"

build:
    docker compose build

up:
    docker compose up -d

down:
    docker compose down

logs:
    docker compose logs -f

restart:
    docker compose restart

clean:
    docker compose down -v
    docker system prune -f

test:
    @echo "Running backend tests..."
    cd backend && python -m pytest
    @echo "Backend tests completed!"
    @echo "Running worker tests..."
    cd worker && python -m pytest
    @echo "Worker tests completed!"

test-e2e:
    @echo "Running frontend E2E tests..."
    cd frontend && npm run test:e2e
    @echo "Frontend E2E tests completed!"

test-all:
    @echo "Running all tests..."
    @$(MAKE) test
    @$(MAKE) test-e2e
    @echo "All tests completed!"

seed:
    @echo "Seeding database with demo data..."
    python scripts/seed_demo.py
    @echo "Database seeding completed!"

lint:
    @echo "Linting backend..."
    cd backend && ruff check .
    @echo "Linting frontend..."
    cd frontend && npm run lint

format:
    @echo "Formatting backend..."
    cd backend && black . && isort .
    @echo "Formatting frontend..."
    cd frontend && npm run format

install:
    @echo "Installing backend dependencies..."
    cd backend && pip install -r requirements-dev.txt
    @echo "Installing frontend dependencies..."
    cd frontend && npm install
    @echo "Dependencies installed!"

backend-shell:
    docker compose exec api bash

worker-shell:
    docker compose exec worker bash

db-shell:
    docker compose exec postgres psql -U postgres -d mtbf

redis-cli:
    docker compose exec redis redis-cli

migrate:
    docker compose exec api alembic upgrade head

migration:
    @read -p "Enter migration message: " msg; \
    docker compose exec api alembic revision --autogenerate -m "$$msg"
