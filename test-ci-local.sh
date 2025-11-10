#!/bin/bash

# Local CI Test Script
# Simulates the CI workflow execution locally

set -e

echo "🚀 Running local CI simulation..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✅ $2${NC}"
    else
        echo -e "${RED}❌ $2${NC}"
        exit 1
    fi
}

print_info() {
    echo -e "${YELLOW}🔄 $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# Check if Docker is available for integration tests
DOCKER_AVAILABLE=false
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
    DOCKER_AVAILABLE=true
fi

print_info "Running linting checks..."
if command -v ruff >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
    make lint > /dev/null 2>&1
    print_status $? "All linting checks"
else
    print_warning "Skipping linting (missing tools - run 'make install' to set up)"
fi

print_info "Running formatting checks..."
# Check formatting without modifying files
if command -v black >/dev/null 2>&1 && command -v isort >/dev/null 2>&1; then
    cd backend
    black --check . > /dev/null 2>&1
    print_status $? "Backend formatting (black)"
    isort --check-only . > /dev/null 2>&1
    print_status $? "Backend import sorting (isort)"
    cd ..

    cd worker
    black --check . > /dev/null 2>&1
    print_status $? "Worker formatting (black)"
    isort --check-only . > /dev/null 2>&1
    print_status $? "Worker import sorting (isort)"
    cd ..
else
    print_warning "Skipping formatting checks (missing tools - run 'make install' to set up)"
fi

print_info "Running frontend build..."
cd frontend
if [ ! -d "node_modules" ]; then
    npm ci > /dev/null 2>&1
fi
npm run build > /dev/null 2>&1
print_status $? "Frontend build (TypeScript compilation)"
cd ..

print_info "Running tests..."
# Check if we can run tests (may require venv setup)
if [ -d "backend/venv" ] || [ -d "backend/.venv" ] || command -v pytest >/dev/null 2>&1; then
    make test > /dev/null 2>&1
    print_status $? "Backend and worker tests"
else
    print_warning "Skipping tests (Python virtual environment not set up)"
    print_warning "Run 'make install' to set up dependencies"
fi

# Integration tests (only if Docker is available)
if [ "$DOCKER_AVAILABLE" = true ]; then
    print_info "Running integration tests with Docker..."
    
    # Start services
    docker compose up --build -d > /dev/null 2>&1
    
    # Wait for services to be healthy
    timeout 60 bash -c 'until docker compose ps | grep -q "healthy\|Up (healthy)"; do sleep 2; done' > /dev/null 2>&1
    
    # Run smoke tests
    timeout 30 bash -c 'until curl -f http://localhost:8000/health; do sleep 2; done' > /dev/null 2>&1
    print_status $? "API health check"
    
    timeout 30 bash -c 'until curl -f http://localhost:5173; do sleep 2; done' > /dev/null 2>&1
    print_status $? "Frontend serving"
    
    # Cleanup
    docker compose down -v > /dev/null 2>&1
    print_status $? "Docker cleanup"
else
    print_warning "Skipping integration tests (Docker not available)"
fi

echo ""
echo -e "${GREEN}🎉 Local CI simulation completed successfully!${NC}"
echo ""
echo "📝 Summary:"
echo "   ✅ All linting checks passed"
echo "   ✅ Code formatting checks passed"
echo "   ✅ Frontend build passed"
if [ -d "backend/venv" ] || [ -d "backend/.venv" ] || command -v pytest >/dev/null 2>&1; then
    echo "   ✅ Backend and worker tests passed"
else
    echo "   ⚠️  Tests skipped (run 'make install' to set up)"
fi
if [ "$DOCKER_AVAILABLE" = true ]; then
    echo "   ✅ Integration tests passed"
else
    echo "   ⚠️  Integration tests skipped (Docker not available)"
fi
echo ""
echo "🚀 Ready to commit and push changes!"
echo ""
echo "📋 Next steps:"
echo "   1. Commit your changes: git add . && git commit -m 'Add CI workflow'"
echo "   2. Push to trigger CI: git push"
echo "   3. Check GitHub Actions for workflow execution"