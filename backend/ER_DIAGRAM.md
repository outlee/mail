# MTBF Platform - Entity Relationship Diagram

## Core Entities

### Assets
- **Asset**: Core asset registry with multi-tenant support
  - Relationships: Has many Runtime Counters, Failure Events, KPI Snapshots
  - Key fields: tenant_id, asset_identifier (unique per tenant), status, type
  - Soft delete support

- **AssetGroup**: Logical groupings of assets
  - Relationships: Has many Asset Members
  - Key fields: tenant_id, name (unique per tenant)
  - Soft delete support

- **AssetGroupMember**: Many-to-many relationship between assets and groups

### Monitoring & Performance

- **AssetRuntimeCounter**: Operational metrics and counters
  - Relationships: Belongs to Asset
  - Key fields: asset_id, counter_type, current_value (non-null)
  - Supports thresholds and targets

- **FailureEvent**: Asset failure tracking with severity classification
  - Relationships: Belongs to Asset, has many Updates
  - Key fields: asset_id, severity, failure_mode, status, downtime_minutes
  - Enum validation for severity and modes

- **FailureEventUpdate**: Status change tracking for failure events
  - Relationships: Belongs to FailureEvent
  - Key fields: failure_event_id, previous_status, new_status

- **KPISnapshot**: Performance metrics and analytics
  - Relationships: Belongs to Asset
  - Key fields: asset_id, kpi_type, period_start/end, value
  - Includes data quality and confidence metrics

### Authorization & Authentication

- **User**: User accounts with multi-tenant support
  - Relationships: Has many UserRoles
  - Key fields: username (unique), email (unique), tenant_id
  - Soft delete support

- **Role**: System roles with permission-based access control
  - Relationships: Has many UserRoles
  - Key fields: name (unique), permissions (JSON), is_system_role
  - Default roles: maintainer, operator, manager

- **UserRole**: Many-to-many user-role assignments
  - Key fields: user_id, role_id, assigned_by, expires_at

### Alerting

- **AlertPolicy**: Alert rules and configuration
  - Relationships: Has many AlertOccurrences
  - Key fields: tenant_id, conditions (JSON), severity, evaluation_frequency
  - Supports rate limiting and escalation

- **AlertOccurrence**: Individual alert instances
  - Relationships: Belongs to AlertPolicy, optionally Asset
  - Key fields: policy_id, severity, status, triggered_at
  - Supports acknowledgment and resolution tracking

### Data Management

- **CSVImportJob**: Bulk data import tracking
  - Key fields: tenant_id, import_type, status, progress_percentage
  - Comprehensive job tracking and error handling

- **AuditLogEntry**: System audit trail
  - Key fields: action, entity_type/id, user_id, tenant_id
  - Tracks old/new values and request metadata

## Key Design Patterns

### Multi-Tenancy
- All major entities support tenant_id for data isolation
- Unique constraints scoped within tenant boundaries

### Soft Delete
- Asset, AssetGroup, and User tables support soft deletion
- Uses deleted_at and is_deleted flags

### Enum Validation
- FailureEvent: severity (LOW/MEDIUM/HIGH/CRITICAL), modes (MECHANICAL/ELECTRICAL/etc.)
- Asset: status (ACTIVE/INACTIVE/MAINTENANCE/DECOMMISSIONED)
- User: status (ACTIVE/INACTIVE/SUSPENDED/PENDING)

### JSON Metadata
- Flexible meta_data columns for extensibility
- Structured data for permissions, conditions, and configuration

### Indexing Strategy
- Composite indexes for common query patterns
- Tenant-scoped indexes for multi-tenant performance
- Time-based indexes for analytics queries

## Data Flow

1. **Asset Registration**: Assets created with unique identifiers per tenant
2. **Monitoring**: Runtime counters track operational metrics
3. **Failure Tracking**: Events logged with severity and resolution tracking
4. **KPI Calculation**: Snapshots generated from counter and failure data
5. **Alerting**: Policies evaluate conditions and trigger notifications
6. **Audit**: All significant actions logged for compliance

## Future Extensions

- **Partitioning**: Time-based partitioning for failure_events and kpi_snapshots
- **IoT Integration**: Additional tables for telemetry data
- **Attachments**: Support for documents and media files
- **Advanced Analytics**: Materialized views for reporting