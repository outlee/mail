# Testing Guide

This document provides comprehensive instructions for running and maintaining tests in the MTBF Platform.

## Table of Contents

- [Overview](#overview)
- [Backend Testing](#backend-testing)
- [Frontend E2E Testing](#frontend-e2e-testing)
- [Test Coverage](#test-coverage)
- [Running Tests Locally](#running-tests-locally)
- [Running Tests in CI](#running-tests-in-ci)
- [Writing New Tests](#writing-new-tests)
- [Troubleshooting](#troubleshooting)

## Overview

The MTBF Platform uses a comprehensive testing strategy:

- **Backend**: pytest for unit and integration tests with ≥80% coverage requirement
- **Frontend**: Playwright for end-to-end (E2E) tests
- **Coverage Reporting**: HTML and JSON reports stored in `reports/` directory
- **Parallel Execution**: Tests run in parallel where possible for faster feedback

## Backend Testing

### Technology Stack

- **Framework**: pytest
- **Coverage**: pytest-cov
- **Database**: PostgreSQL test database (`mtbf_test`)
- **Test Client**: FastAPI TestClient

### Test Structure

```
backend/tests/
├── __init__.py
├── conftest.py              # Fixtures and test configuration
├── test_auth.py            # Authentication tests
├── test_health.py          # Health check tests
├── test_kpi_scheduling.py  # KPI scheduling tests
└── test_services.py        # Service layer tests
```

### Running Backend Tests

#### All Tests

```bash
# Using Make
make test

# Using pytest directly
cd backend
pytest
```

#### Specific Test File

```bash
cd backend
pytest tests/test_auth.py
```

#### Specific Test Function

```bash
cd backend
pytest tests/test_auth.py::test_login_success
```

#### With Verbose Output

```bash
cd backend
pytest -v
```

#### With Coverage Report

```bash
cd backend
pytest --cov=app --cov-report=html
```

### Test Fixtures

The following fixtures are available in `conftest.py`:

- `db`: Database session with transaction rollback
- `client`: FastAPI test client
- `sample_user`: Test user with operator role
- `maintainer_user`: Test user with maintainer role
- `sample_asset`: Test asset
- `sample_group`: Test group
- `sample_kpi_snapshot`: Test KPI snapshot
- `sample_task_run`: Test task run

### Coverage Requirements

- **Minimum Coverage**: 80%
- **Enforcement**: Tests fail if coverage is below 80%
- **Reports Location**: `reports/coverage/backend/`

## Frontend E2E Testing

### Technology Stack

- **Framework**: Playwright
- **Browser**: Chromium (Desktop Chrome)
- **Language**: TypeScript

### Test Structure

```
frontend/tests/
├── auth.spec.ts        # Authentication flow tests
├── alerts.spec.ts      # Alerts management tests
└── dashboard.spec.ts   # Dashboard navigation tests
```

### Running E2E Tests

#### All E2E Tests

```bash
# Using Make
make test-e2e

# Using npm directly
cd frontend
npm run test:e2e
```

#### Headless Mode (CI)

```bash
cd frontend
npm run test:e2e
```

#### Debug Mode

```bash
cd frontend
npm run test:e2e:debug
```

#### Specific Test File

```bash
cd frontend
npx playwright test tests/auth.spec.ts
```

#### With UI Mode

```bash
cd frontend
npx playwright test --ui
```

### Test Coverage

E2E tests cover the following user journeys:

1. **Authentication**
   - Login with valid/invalid credentials
   - Form validation
   - Session persistence
   - Logout flow

2. **Dashboard Navigation**
   - Page load and display
   - User information display
   - System health check
   - Responsive design
   - Role-based access control

3. **Alerts Management**
   - Navigation to alerts pages
   - Creating alert policies
   - Viewing alerts list
   - Acknowledging alerts
   - Form validation
   - Role-based restrictions

### Reports

Playwright generates multiple report formats:

- **HTML Report**: `reports/playwright/index.html`
- **JUnit XML**: `reports/junit/e2e-results.xml`
- **Screenshots**: Captured on test failure
- **Videos**: Recorded on test failure
- **Traces**: Saved on test failure for debugging

To view the HTML report:

```bash
cd frontend
npx playwright show-report ../reports/playwright
```

## Test Coverage

### Backend Coverage Report

After running tests, view the coverage report:

```bash
# Open HTML report in browser
open reports/coverage/backend/index.html
```

The report shows:

- Overall coverage percentage
- Line-by-line coverage for each file
- Uncovered lines highlighted
- Branch coverage

### Coverage by Module

Target coverage by module:

- **Models**: 100% (simple data models)
- **Services**: ≥90% (core business logic)
- **Routes**: ≥80% (API endpoints)
- **Security**: ≥90% (authentication/authorization)
- **Database**: ≥80% (database connections)

## Running Tests Locally

### Prerequisites

1. **Backend Tests**:
   - Python 3.11+
   - PostgreSQL running on localhost:5432
   - Test database: `mtbf_test`
   - Dependencies: `pip install -r backend/requirements-dev.txt`

2. **Frontend E2E Tests**:
   - Node.js 20+
   - Playwright browsers: `npx playwright install`
   - Backend API running on http://localhost:8000

### Setup Test Database

```bash
# Create test database
createdb -U postgres mtbf_test

# Or using psql
psql -U postgres -c "CREATE DATABASE mtbf_test;"
```

### Running All Tests

```bash
# Backend + Frontend E2E
make test-all
```

## Running Tests in CI

### GitHub Actions

Tests are automatically run in CI on:

- Pull requests
- Push to main branch
- Scheduled daily runs

CI configuration:

```yaml
- name: Run Backend Tests
  run: |
    cd backend
    pytest --junitxml=../reports/junit/backend-results.xml

- name: Run E2E Tests
  run: |
    cd frontend
    npm run test:e2e
```

### Parallel Execution

- **Backend**: pytest-xdist enables parallel test execution
- **Frontend**: Playwright runs tests in parallel by default

### Test Reports in CI

JUnit XML reports are uploaded as artifacts:

- `reports/junit/backend-results.xml`
- `reports/junit/e2e-results.xml`

## Writing New Tests

### Backend Test Template

```python
import pytest
from sqlalchemy.orm import Session

from app.models import MyModel
from app.services import MyService


class TestMyService:
    def test_create_entity(self, db: Session):
        # Arrange
        data = {"name": "Test"}
        
        # Act
        entity = MyService.create(db, **data)
        
        # Assert
        assert entity.id is not None
        assert entity.name == "Test"

    def test_get_entity_not_found(self, db: Session):
        # Act
        entity = MyService.get(db, "nonexistent-id")
        
        # Assert
        assert entity is None
```

### Frontend E2E Test Template

```typescript
import { test, expect } from '@playwright/test'

test.describe('Feature Name', () => {
  test.beforeEach(async ({ page }) => {
    // Login or setup
    await page.goto('/login')
    await page.fill('input[name="email"]', 'test@example.com')
    await page.fill('input[name="password"]', 'password')
    await page.click('button:has-text("Login")')
    await page.waitForURL('/dashboard')
  })

  test('should perform action', async ({ page }) => {
    // Arrange
    await page.goto('/feature')
    
    // Act
    await page.click('button:has-text("Action")')
    
    // Assert
    await expect(page.locator('text=Success')).toBeVisible()
  })
})
```

### Best Practices

1. **Use Descriptive Test Names**: Test names should clearly describe what is being tested
2. **Follow AAA Pattern**: Arrange, Act, Assert
3. **Use Fixtures**: Leverage pytest fixtures for test setup
4. **Isolate Tests**: Each test should be independent
5. **Test Edge Cases**: Include tests for error conditions
6. **Keep Tests Fast**: Avoid unnecessary waits or sleeps
7. **Use Page Objects**: For complex E2E tests, consider page object pattern

## Troubleshooting

### Backend Tests

#### Database Connection Failed

```bash
# Check PostgreSQL is running
pg_isready -h localhost -p 5432

# Verify test database exists
psql -U postgres -l | grep mtbf_test

# Create if missing
createdb -U postgres mtbf_test
```

#### Import Errors

```bash
# Reinstall dependencies
cd backend
pip install -r requirements-dev.txt
```

#### Coverage Below 80%

```bash
# Run with coverage report to identify uncovered lines
cd backend
pytest --cov=app --cov-report=term-missing

# View HTML report for detailed analysis
pytest --cov=app --cov-report=html
open htmlcov/index.html
```

### E2E Tests

#### Browser Not Installed

```bash
# Install Playwright browsers
cd frontend
npx playwright install chromium
```

#### Backend Not Running

```bash
# Start backend in another terminal
cd backend
uvicorn app.main:app --reload

# Or use Docker
docker compose up api
```

#### Test Timeouts

- Increase timeout in test: `await page.waitForURL('/dashboard', { timeout: 10000 })`
- Check network conditions
- Verify backend is responsive

#### Failed to Start Web Server

```bash
# Kill any process using port 5173
lsof -ti:5173 | xargs kill -9

# Or change port in playwright.config.ts
```

### General Issues

#### Permission Denied on Reports Directory

```bash
# Create reports directory with proper permissions
mkdir -p reports/{coverage,junit,playwright}
chmod -R 755 reports
```

#### Tests Pass Locally but Fail in CI

- Check environment variables
- Verify database setup in CI
- Review CI logs for specific errors
- Ensure all dependencies are installed

## Sample Test Reports

Sample test reports and screenshots are available in `docs/test-samples/`:

- `backend-coverage.png`: Backend coverage report screenshot
- `playwright-report.png`: Playwright HTML report screenshot
- `test-results.txt`: Sample test output

## Additional Resources

- [pytest Documentation](https://docs.pytest.org/)
- [Playwright Documentation](https://playwright.dev/)
- [FastAPI Testing](https://fastapi.tiangolo.com/tutorial/testing/)
- [Ant Design Testing](https://ant.design/docs/react/testing)

## Contributing

When adding new features:

1. Write tests first (TDD approach recommended)
2. Ensure tests pass locally before pushing
3. Maintain ≥80% coverage for new code
4. Add E2E tests for user-facing features
5. Update this documentation if adding new test patterns
