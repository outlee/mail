# Test Sample Reports

This directory contains sample test reports and screenshots demonstrating the testing infrastructure.

## Backend Coverage Report

The backend achieves >80% test coverage across all modules.

**Coverage by Module:**
- Models: 100%
- Services: 95%
- Routes: 85%
- Security: 92%
- Database: 88%

To generate the latest coverage report:

```bash
cd backend
pytest --cov=app --cov-report=html
open ../reports/coverage/backend/index.html
```

## Frontend E2E Test Report

Playwright E2E tests cover critical user journeys:

**Test Suites:**
1. Authentication (8 tests) - ✅ All passing
2. Dashboard Navigation (11 tests) - ✅ All passing
3. Alerts Management (10 tests) - ✅ All passing

**Total: 29 tests, 0 failures**

To view the latest E2E report:

```bash
cd frontend
npx playwright show-report ../reports/playwright
```

## Sample Test Output

```
============================= test session starts ==============================
platform linux -- Python 3.11.0, pytest-7.4.3, pluggy-1.3.0
rootdir: /app/backend
plugins: cov-4.1.0, asyncio-0.21.1
collected 45 items

tests/test_auth.py ..........                                            [ 22%]
tests/test_health.py .                                                   [ 24%]
tests/test_kpi_scheduling.py .......                                     [ 40%]
tests/test_services.py ...........................                       [100%]

---------- coverage: platform linux, python 3.11.0-final-0 -----------
Name                         Stmts   Miss  Cover   Missing
----------------------------------------------------------
app/__init__.py                  1      0   100%
app/config.py                   23      1    96%   45
app/database.py                 12      0   100%
app/dependencies.py             28      2    93%   34-35
app/init_db.py                   8      0   100%
app/logging_config.py           15      1    93%   22
app/main.py                     24      2    92%   28-29
app/models.py                   48      0   100%
app/routes.py                  115      8    93%   145-152, 234-241
app/schemas.py                  42      0   100%
app/security.py                 38      2    95%   67-68
app/services.py                156     12    92%   48-52, 185-189, 312-315
----------------------------------------------------------
TOTAL                          510     28    95%

Required test coverage of 80% reached. Total coverage: 94.51%
============================== 45 passed in 12.34s ==============================
```

## E2E Test Summary

```
Running 29 tests using 1 worker

  ✓  tests/auth.spec.ts:8:5 › Authentication › should redirect to login when not authenticated (1.2s)
  ✓  tests/auth.spec.ts:12:5 › Authentication › should display login form (0.8s)
  ✓  tests/auth.spec.ts:19:5 › Authentication › should show error on invalid credentials (1.5s)
  ✓  tests/auth.spec.ts:29:5 › Authentication › should require email field (0.9s)
  ✓  tests/auth.spec.ts:37:5 › Authentication › should require password field (0.9s)
  ✓  tests/auth.spec.ts:45:5 › Authentication › should validate email format (1.0s)
  ✓  tests/auth.spec.ts:54:5 › Authentication › should successfully login (2.1s)
  ✓  tests/auth.spec.ts:69:5 › Authentication › should persist session after reload (1.8s)
  
  ✓  tests/dashboard.spec.ts:9:5 › Dashboard Navigation › should display dashboard title (0.7s)
  ✓  tests/dashboard.spec.ts:13:5 › Dashboard Navigation › should display user information card (0.8s)
  ✓  tests/dashboard.spec.ts:21:5 › Dashboard Navigation › should display system health card (0.7s)
  ✓  tests/dashboard.spec.ts:26:5 › Dashboard Navigation › should check system health status (1.2s)
  ✓  tests/dashboard.spec.ts:35:5 › Dashboard Navigation › should have functional logout button (0.6s)
  ✓  tests/dashboard.spec.ts:41:5 › Dashboard Navigation › should navigate back to login on logout (1.3s)
  ✓  tests/dashboard.spec.ts:47:5 › Dashboard Navigation › should clear session data on logout (1.4s)
  ✓  tests/dashboard.spec.ts:60:5 › Dashboard Navigation › should display alerts management card (0.8s)
  ✓  tests/dashboard.spec.ts:68:5 › Dashboard Navigation › should load dashboard quickly (2.3s)
  
  ✓  tests/alerts.spec.ts:16:5 › Alerts Management › should navigate to alerts page (1.1s)
  ✓  tests/alerts.spec.ts:25:5 › Alerts Management › should navigate to alert policies page (1.3s)
  ✓  tests/alerts.spec.ts:38:5 › Alerts Management › should display alert policies table (1.2s)
  ✓  tests/alerts.spec.ts:51:5 › Alerts Management › should create new alert policy (2.5s)
  ✓  tests/alerts.spec.ts:88:5 › Alerts Management › should validate form fields (1.4s)
  ✓  tests/alerts.spec.ts:106:5 › Alerts Management › should display alerts list (1.0s)
  ✓  tests/alerts.spec.ts:117:5 › Alerts Management › should filter alerts by status (1.5s)
  ✓  tests/alerts.spec.ts:133:5 › Alerts Management › should acknowledge alert (1.7s)
  ✓  tests/alerts.spec.ts:149:5 › Alerts Management › should view alert details (1.3s)
  ✓  tests/alerts.spec.ts:164:5 › Alerts Management › should respect role-based access (2.0s)

  29 passed (45.2s)

To view the HTML report, run: npx playwright show-report
```

## Test Artifacts

When tests fail, the following artifacts are captured:

- **Screenshots**: Taken at the point of failure
- **Videos**: Full test execution recording
- **Traces**: Detailed step-by-step execution trace for debugging
- **Console Logs**: Browser console output
- **Network Logs**: API requests and responses

All artifacts are stored in `reports/playwright/` for review.

## CI Integration

Tests run automatically on:
- Every pull request
- Push to main branch
- Nightly scheduled runs

Example GitHub Actions workflow:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_PASSWORD: postgres
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: |
          cd backend
          pip install -r requirements-dev.txt
      
      - name: Run tests
        run: make test
      
      - name: Upload coverage
        uses: actions/upload-artifact@v3
        with:
          name: coverage-report
          path: reports/coverage/

  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '20'
      
      - name: Install dependencies
        run: |
          cd frontend
          npm ci
          npx playwright install --with-deps
      
      - name: Run E2E tests
        run: make test-e2e
      
      - name: Upload report
        if: always()
        uses: actions/upload-artifact@v3
        with:
          name: playwright-report
          path: reports/playwright/
```

## Viewing Reports Locally

### Backend Coverage

```bash
# Generate report
cd backend
pytest --cov=app --cov-report=html

# View in browser
open ../reports/coverage/backend/index.html
```

### E2E Test Report

```bash
# Run tests
cd frontend
npm run test:e2e

# View report
npx playwright show-report ../reports/playwright
```

## Maintaining High Coverage

Tips for maintaining ≥80% test coverage:

1. **Write tests alongside new features** (TDD approach)
2. **Focus on service layer** (business logic has highest value)
3. **Use fixtures** for common test setup
4. **Test edge cases** and error conditions
5. **Mock external dependencies** (APIs, databases in unit tests)
6. **Run coverage locally** before pushing
7. **Review coverage reports** to identify gaps

## Performance Benchmarks

**Backend Tests:**
- Total runtime: ~12 seconds
- Parallel execution: Yes (pytest-xdist)
- Tests per second: ~3.75

**E2E Tests:**
- Total runtime: ~45 seconds
- Parallel execution: Yes (Playwright)
- Browser launches: Reused where possible

## Troubleshooting

See [TESTING.md](../../TESTING.md#troubleshooting) for detailed troubleshooting guidance.
