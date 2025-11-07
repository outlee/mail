# Dashboard UI Implementation Guide

## Overview

This document describes the Dashboard UI implementation for the MTBF Platform, including Overview metrics, Asset detail pages, and Failure analysis with Pareto charts.

## Architecture

### Backend Components

#### Models (app/models.py)
- **Asset**: Represents individual equipment/systems
  - `id`: UUID primary key
  - `name`: Asset name
  - `description`: Optional description
  - `created_at`, `updated_at`: Timestamps

- **FailureEvent**: Records of equipment failures
  - `id`: UUID primary key
  - `asset_id`: Reference to Asset
  - `failure_mode`: Type of failure (string)
  - `failure_code`: Optional failure code
  - `severity`: Criticality level
  - `duration_minutes`: How long the failure lasted
  - `start_time`, `end_time`: Failure window timestamps

- **KPISnapshot**: Existing model for KPI data
  - Used for MTBF calculations and trending

- **TaskRun**: Existing model for job tracking
  - Enhanced with dashboard endpoints

- **Group**: Collection of assets for aggregated metrics

#### Services (app/services.py)

**AssetService**
```python
AssetService.get_asset_by_id(db, asset_id)  # Single asset
AssetService.list_assets(db, skip, limit)    # All assets with pagination
AssetService.create_asset(db, name, description)  # Create new asset
```

**FailureEventService**
```python
FailureEventService.create_failure_event(db, asset_id, failure_mode, ...)
FailureEventService.get_failure_event(db, event_id)
FailureEventService.list_failure_events(db, asset_id=None, skip=0, limit=100)
FailureEventService.get_failures_by_mode(db)  # Returns dict for Pareto
```

**DashboardService**
```python
DashboardService.get_kpi_stats(db)           # Overall statistics
DashboardService.get_top_assets(db, limit)   # Best performers
DashboardService.get_bottom_assets(db, limit)  # Worst performers
```

#### API Routes (app/routes.py)

**Asset Endpoints**
- `GET /api/v1/assets` - List all assets
- `GET /api/v1/assets/{asset_id}` - Asset detail with KPI and failures

**Failure Endpoints**
- `GET /api/v1/failures` - List failures (optional: ?asset_id=)
- `GET /api/v1/failures/{failure_id}` - Single failure detail

**Dashboard Endpoints**
- `GET /api/v1/dashboard/stats` - KPI statistics
- `GET /api/v1/dashboard/top-assets?limit=10` - Top performers
- `GET /api/v1/dashboard/bottom-assets?limit=10` - Bottom performers

All endpoints require authentication (`get_current_user`) and return typed responses.

### Frontend Components

#### Pages

**Overview.tsx** (`/overview`)
- Display global KPI metrics in stat cards
  - Average KPI, Min/Max KPI
  - Total assets and failures
  - Failure modes summary
- Filter by time window (24h, 7d, 30d, all)
- Two tables: top and bottom performing assets
- Links to asset details via table clicks
- Links to failure analysis page

**AssetDetail.tsx** (`/assets/:id`)
- Breadcrumb navigation back to overview
- Asset metadata (name, description, creation date)
- Latest MTBF value with trend color coding
- Recent failure count with severity indicators
- Timeline chart placeholder (expandable for future)
- Table of recent failures with click-to-detail drawer
- Failure detail drawer with full information

**FailureAnalysis.tsx** (`/failure-analysis`)
- Dual view: Pareto bars + Table view
- Top stats: Total modes, total failures, 80/20 rule coverage
- Pareto bars: Shows cumulative percentage with color coding
- Table view: Sortable columns with severity tags
- CSV export button with CSV download
- Filtered failures table showing recent failures
- 80/20 rule explanation in footer

#### Services (src/services/dashboardAPI.ts)

```typescript
dashboardAPI.getAssets(skip?, limit?)
dashboardAPI.getAssetDetail(assetId)
dashboardAPI.getFailures(assetId?, skip?, limit?)
dashboardAPI.getFailure(failureId)
dashboardAPI.getDashboardStats()
dashboardAPI.getTopAssets(limit?)
dashboardAPI.getBottomAssets(limit?)
```

All methods use the authenticated `apiClient` with error handling.

#### Types (src/types/dashboard.ts)

```typescript
interface Asset { id, name, description, created_at, updated_at }
interface KPISnapshot { id, asset_id, group_id, kpi_type, value, period_* }
interface FailureEvent { id, asset_id, failure_mode, severity, duration_minutes, ... }
interface AssetDetail extends Asset { latest_kpi?, recent_failures }
interface KPIStats { average_kpi, min_kpi, max_kpi, total_assets, ... }
interface AssetSummary { id, name, avg_kpi, failure_count }
```

#### Routing Updates (src/App.tsx)

```typescript
<Route path="/overview" element={<ProtectedRoute><Overview /></ProtectedRoute>} />
<Route path="/assets/:id" element={<ProtectedRoute><AssetDetail /></ProtectedRoute>} />
<Route path="/failure-analysis" element={<ProtectedRoute><FailureAnalysis /></ProtectedRoute>} />
```

Original dashboard page updated with navigation buttons to new pages.

## Key Features

### 1. Overview Dashboard
- **Real-time KPI Metrics**: Displays current system health
- **Asset Ranking**: Automatic sorting by performance
- **Time Filtering**: Change view window without page reload
- **Responsive Layout**: Works on mobile (xs), tablet (md), desktop (lg)
- **Error Handling**: Graceful degradation with error alerts

### 2. Asset Detail Page
- **Historical Context**: Links back to overview via breadcrumb
- **Failure Timeline**: Recent failures displayed in chronological order
- **Drill-down Details**: Click failure to see full details in drawer
- **Asset Metadata**: Creation date, last update, unique ID
- **MTBF Trends**: Latest KPI value with color-coded health status

### 3. Failure Analysis
- **Pareto Principle**: Identifies which failure modes have highest impact
- **80/20 Rule**: Calculates which modes account for 80% of failures
- **Client-side Calculation**: All percentages computed in browser (no server load)
- **Export Functionality**: CSV download of Pareto data for reporting
- **Dual View**: Bars for visual insight, table for detailed data

## Data Flow

```
User navigates to /overview
   ↓
Overview.tsx uses useEffect to load:
   - dashboardAPI.getDashboardStats()
   - dashboardAPI.getTopAssets()
   - dashboardAPI.getBottomAssets()
   ↓
API calls hit secured endpoints in routes.py
   ↓
Backend services query database
   ↓
Responses formatted as JSON
   ↓
Frontend displays with Ant Design components
   ↓
User clicks asset link
   ↓
Router navigates to /assets/{id}
   ↓
AssetDetail.tsx loads:
   - dashboardAPI.getAssetDetail(id)
   ↓
Component renders with latest KPI and failures
```

## Error Handling

### Backend
- All endpoints return 404 for missing resources
- Authentication required (401 if no token)
- Role-based access (MAINTAINER, OPERATOR, MANAGER)

### Frontend
- Try-catch blocks in async functions
- Error alerts with user-friendly messages
- Loading spinners during data fetches
- Graceful fallbacks for missing data

### Specific Cases
- Non-existent asset: Shows "Asset Not Found" alert
- Failed API call: "Failed to load X data" alert with retry option
- No data: Empty states with helpful messages
- Network timeout: Error alert with retry button

## Testing

### Unit/Component Testing (Ready for React Testing Library)

Test coverage for:
1. **Overview Component**
   - Loads and displays KPI statistics
   - Renders top/bottom asset tables
   - Updates on time window change
   - Shows error alerts on failure

2. **AssetDetail Component**
   - Displays correct asset information
   - Shows recent failures in table
   - Opens detail drawer on failure click
   - Shows 404 for non-existent asset

3. **FailureAnalysis Component**
   - Calculates Pareto percentages correctly
   - Switches between pareto and table view
   - Exports CSV with correct data
   - Shows 80/20 rule coverage

### End-to-End Testing (Playwright)

File: `frontend/tests/dashboard.spec.ts`

Test scenarios:
1. Navigation between pages
2. Data loading and display
3. Responsive layout on mobile/tablet
4. Error handling and edge cases
5. CSV export functionality
6. Table sorting and filtering
7. Asset detail drill-down

Run with: `npm run test:e2e`

## Performance Considerations

### Frontend
- Data fetched only once on page load (no auto-refresh)
- Pagination on asset tables (limit: 100 default)
- Client-side Pareto calculations (no server processing)
- CSV export generates client-side (reduces server load)

### Backend
- Asset queries with pagination (skip/limit)
- Failure queries filtered by asset_id when provided
- SQL aggregation functions used (avg, count) not Python loops
- Advisory locking prevents concurrent data conflicts

### Caching
- No explicit caching implemented (future enhancement)
- Could add React Query/SWR for automatic cache management

## Future Enhancements

1. **Real-time Updates**
   - WebSocket connection for live KPI updates
   - Alert banner for critical failures

2. **Advanced Charting**
   - Line chart for KPI timeline
   - Bar chart for failure count trends
   - Heatmap for asset status matrix

3. **Root Cause Analysis**
   - Drill-down from failures to related events
   - Linked incidents and resolutions

4. **Customizable Dashboards**
   - User-defined widgets
   - Saved filter views
   - Dark mode theme

5. **Embedding**
   - Export dashboard as iframe
   - Public read-only links
   - Email reports

## Configuration

### Environment Variables
No special variables required beyond existing:
- `VITE_API_URL`: Backend API base URL (for dashboard API calls)

### Database Setup
Ensure these tables exist:
- `assets` - Created by init_db.py
- `failure_events` - Created by init_db.py
- `kpi_snapshots` - Already exists
- `task_runs` - Already exists

### Sample Data
To populate dashboard with test data:

```python
# In Python shell
from app.services import AssetService, FailureEventService
from datetime import datetime, timedelta

asset = AssetService.create_asset(db, "Production Server A", "Main production server")
FailureEventService.create_failure_event(
    db,
    asset_id=asset.id,
    failure_mode="Network Timeout",
    severity="high",
    start_time=datetime.utcnow() - timedelta(hours=2),
    end_time=datetime.utcnow() - timedelta(hours=1),
    duration_minutes=60.0
)
```

## Troubleshooting

### Dashboard shows no data
1. Check database has assets and failure_events
2. Verify KPI snapshots exist for assets
3. Check API endpoints return 200 status
4. Check browser console for errors

### Asset detail shows 404
1. Verify asset ID exists in database
2. Check asset ID format (should be UUID string)
3. Try direct API call: GET /api/v1/assets/{id}

### CSV export doesn't work
1. Check browser allows downloads
2. Verify pareto data is not empty
3. Check browser console for JavaScript errors

### Responsive layout issues
1. Check Ant Design Grid responsive props (xs, md, lg)
2. Verify viewport meta tag in index.html
3. Test with browser DevTools device emulation

## Code Quality

### Linting
- Frontend: `npm run lint` (ESLint + TypeScript)
- Backend: `make lint` (Ruff)

### Formatting
- Frontend: `npm run format` (Prettier)
- Backend: `make format` (Black + isort)

### Type Safety
- Frontend: Full TypeScript with strict types
- Backend: Type hints on all functions
- API schemas: Pydantic models for validation

## References

- [Ant Design Components](https://ant.design/components/overview/)
- [React Router Docs](https://reactrouter.com/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)
