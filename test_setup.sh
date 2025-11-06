#!/bin/bash

# MTBF Platform Setup Verification Script

set -e

echo "=================================="
echo "MTBF Platform Setup Verification"
echo "=================================="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

# Check directory structure
echo "1. Checking directory structure..."
[ -d "backend" ] && print_status 0 "backend/ directory exists" || print_status 1 "backend/ directory missing"
[ -d "worker" ] && print_status 0 "worker/ directory exists" || print_status 1 "worker/ directory missing"
[ -d "frontend" ] && print_status 0 "frontend/ directory exists" || print_status 1 "frontend/ directory missing"
[ -d "infrastructure" ] && print_status 0 "infrastructure/ directory exists" || print_status 1 "infrastructure/ directory missing"
echo ""

# Check backend files
echo "2. Checking backend files..."
[ -f "backend/app/main.py" ] && print_status 0 "FastAPI main.py exists" || print_status 1 "FastAPI main.py missing"
[ -f "backend/app/config.py" ] && print_status 0 "Settings config.py exists" || print_status 1 "Settings config.py missing"
[ -f "backend/tests/test_health.py" ] && print_status 0 "Test file exists" || print_status 1 "Test file missing"
[ -f "backend/Dockerfile" ] && print_status 0 "Backend Dockerfile exists" || print_status 1 "Backend Dockerfile missing"
echo ""

# Check worker files
echo "3. Checking worker files..."
[ -f "worker/worker/celery_app.py" ] && print_status 0 "Celery app exists" || print_status 1 "Celery app missing"
[ -f "worker/worker/tasks.py" ] && print_status 0 "Celery tasks exists" || print_status 1 "Celery tasks missing"
[ -f "worker/Dockerfile" ] && print_status 0 "Worker Dockerfile exists" || print_status 1 "Worker Dockerfile missing"
echo ""

# Check frontend files
echo "4. Checking frontend files..."
[ -f "frontend/src/main.tsx" ] && print_status 0 "React main.tsx exists" || print_status 1 "React main.tsx missing"
[ -f "frontend/src/pages/Dashboard.tsx" ] && print_status 0 "Dashboard page exists" || print_status 1 "Dashboard page missing"
[ -f "frontend/src/services/api.ts" ] && print_status 0 "API client exists" || print_status 1 "API client missing"
[ -f "frontend/Dockerfile" ] && print_status 0 "Frontend Dockerfile exists" || print_status 1 "Frontend Dockerfile missing"
echo ""

# Check configuration files
echo "5. Checking configuration files..."
[ -f "docker-compose.yml" ] && print_status 0 "docker-compose.yml exists" || print_status 1 "docker-compose.yml missing"
[ -f ".env.example" ] && print_status 0 ".env.example exists" || print_status 1 ".env.example missing"
[ -f ".gitignore" ] && print_status 0 ".gitignore exists" || print_status 1 ".gitignore missing"
[ -f "Makefile" ] && print_status 0 "Makefile exists" || print_status 1 "Makefile missing"
echo ""

# Check documentation
echo "6. Checking documentation..."
[ -f "README.md" ] && print_status 0 "README.md exists" || print_status 1 "README.md missing"
[ -f "SETUP.md" ] && print_status 0 "SETUP.md exists" || print_status 1 "SETUP.md missing"
[ -f "VERIFICATION.md" ] && print_status 0 "VERIFICATION.md exists" || print_status 1 "VERIFICATION.md missing"
echo ""

# Test backend if venv exists
if [ -d "backend/venv" ]; then
    echo "7. Running backend tests..."
    cd backend
    source venv/bin/activate
    pytest -v --tb=short 2>&1 | grep -E "PASSED|FAILED|ERROR" || true
    cd ..
    echo ""
fi

# Count services in docker-compose
echo "8. Checking Docker Compose services..."
SERVICE_COUNT=$(grep -c "^  [a-z]" docker-compose.yml || echo "0")
echo "   Found $SERVICE_COUNT services in docker-compose.yml"
echo "   Expected: postgres, redis, api, worker, scheduler, web"
echo ""

# Final summary
echo "=================================="
echo "Verification Complete!"
echo "=================================="
echo ""
echo "To start the platform:"
echo "  1. docker compose up --build"
echo ""
echo "To run backend tests:"
echo "  cd backend && source venv/bin/activate && pytest"
echo ""
echo "To run linting:"
echo "  make lint"
echo ""
echo "For more information, see README.md"
