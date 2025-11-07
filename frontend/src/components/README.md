# UI Components Documentation

## Alerts Management System

### AlertPolicies Component
**Location**: `src/pages/AlertPolicies.tsx`

**Description**: Main component for managing alert policies. Provides a table view of all policies with create, edit, delete, and toggle functionality.

**Features**:
- Table view of alert policies with sorting and filtering
- Create/Edit drawer with comprehensive form validation
- Role-based access control (operators read-only)
- Real-time policy enable/disable toggle
- Recipient configuration (email/webhook)

**Props**: None (uses auth context for role-based access)

**Usage**:
```tsx
<AlertPolicies />
```

### Alerts Component
**Location**: `src/pages/Alerts.tsx`

**Description**: Component for viewing and managing alert events. Provides list view with filtering, bulk actions, and detailed alert information.

**Features**:
- Alert events table with status and severity indicators
- Advanced filtering by status, severity, date range
- Bulk acknowledgment functionality
- Alert detail modal with history timeline
- Role-based access control

**Props**: None (uses auth context for role-based access)

**Usage**:
```tsx
<Alerts />
```

### AlertsNavigation Component
**Location**: `src/components/AlertsNavigation.tsx`

**Description**: Navigation component for alerts section with role-based menu items.

**Features**:
- Horizontal menu with alerts and policies options
- Role-based item visibility (policies hidden for operators)
- Active route highlighting

**Props**:
- `userRole: string` - Current user's role for access control

**Usage**:
```tsx
<AlertsNavigation userRole="manager" />
```

### AlertsLayout Component
**Location**: `src/pages/AlertsLayout.tsx`

**Description**: Layout wrapper for alerts pages that handles user authentication and role loading.

**Features**:
- Loads user information from auth API
- Provides navigation component
- Handles loading and error states

**Props**: None

**Usage**:
```tsx
<AlertsLayout />
```

## Styling

All components follow the existing Ant Design theme and styling conventions used throughout the application:

- **Color Scheme**: Consistent with dashboard and existing UI
- **Typography**: Uses Ant Design typography components
- **Spacing**: Follows 24px grid system for margins and padding
- **Responsive Design**: All tables and forms are responsive
- **Icons**: Uses Ant Design icons for consistency

## Form Validation

Client-side validation mirrors expected backend rules:

- **Policy Name**: Required, max 100 characters, unique
- **Threshold**: Required, positive number
- **Cooldown**: Required, minimum 1 minute
- **Email**: Valid email format for email recipients
- **Webhook URL**: Valid URL format for webhook recipients

## Role-Based Access Control

The system enforces role-based permissions:

- **Operators**: Read-only access to alerts, no access to policies
- **Maintainers**: Full access to alerts and policies
- **Managers**: Full access to alerts and policies

Access control is implemented at both the UI level (disabling buttons/hiding features) and will be enforced at the API level when backend endpoints are implemented.