# Alerting System Documentation

## Overview

The MTBF Platform includes a comprehensive alerting system that monitors KPI values and triggers notifications when thresholds are crossed. The system supports email and webhook notifications with deduplication windows to prevent alert fatigue.

## Architecture

### Core Components

1. **Alert Policies**: Define monitoring rules with thresholds, comparators, and notification settings
2. **Alert Occurrences**: Individual alert instances created when policies are triggered
3. **Deduplication**: Prevents multiple alerts for the same condition within a time window
4. **Notification Service**: Handles email and webhook delivery
5. **Event Logging**: Tracks all alert lifecycle events for audit trails

### Data Models

#### AlertPolicy
- **name**: Unique identifier for the policy
- **metric_name**: KPI metric to monitor (e.g., "rolling", "calendar")
- **comparator**: Threshold comparison (gt, gte, lt, lte, eq, ne)
- **threshold**: Numeric threshold value
- **severity**: Alert severity level (low, medium, high, critical)
- **deduplication_window_minutes**: Time window to suppress duplicate alerts
- **email_recipients**: List of email addresses for notifications
- **webhook_url**: URL for webhook notifications
- **webhook_secret**: Secret for webhook signature verification

#### AlertOccurrence
- **policy_id**: Reference to the triggering policy
- **asset_id/group_id**: Target resource identifier
- **kpi_snapshot_id**: Reference to the KPI data that triggered the alert
- **status**: Current state (active, acknowledged, resolved)
- **severity**: Alert severity level
- **current_value**: Actual KPI value that triggered the alert
- **threshold_value**: Policy threshold that was crossed
- **message**: Human-readable alert description

## API Endpoints

### Policy Management

#### Create Alert Policy
```http
POST /api/v1/alerts/policies
Authorization: Bearer <token>
Content-Type: application/json

{
  "name": "High CPU Usage",
  "description": "Alert when CPU usage exceeds 90%",
  "metric_name": "cpu_usage",
  "comparator": "gt",
  "threshold": 90.0,
  "severity": "high",
  "deduplication_window_minutes": 60,
  "email_recipients": ["ops@example.com"],
  "webhook_url": "https://hooks.slack.com/...",
  "webhook_secret": "webhook-secret",
  "is_active": true
}
```

#### List Policies
```http
GET /api/v1/alerts/policies?active_only=true&skip=0&limit=100
Authorization: Bearer <token>
```

#### Get Policy
```http
GET /api/v1/alerts/policies/{policy_id}
Authorization: Bearer <token>
```

#### Update Policy
```http
PUT /api/v1/alerts/policies/{policy_id}
Authorization: Bearer <token>
Content-Type: application/json

{
  "threshold": 95.0,
  "severity": "critical"
}
```

#### Delete Policy
```http
DELETE /api/v1/alerts/policies/{policy_id}
Authorization: Bearer <token>
```

### Alert Events

#### List Alert Events
```http
GET /api/v1/alerts/events?status=active&severity=high&asset_id=xxx&skip=0&limit=100
Authorization: Bearer <token>
```

#### Acknowledge Alert
```http
POST /api/v1/alerts/events/{alert_id}/acknowledge
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": "user-uuid",
  "message": "Investigating the issue"
}
```

#### Resolve Alert
```http
POST /api/v1/alerts/events/{alert_id}/resolve
Authorization: Bearer <token>
Content-Type: application/json

{
  "user_id": "user-uuid",
  "message": "Issue resolved by restarting service"
}
```

## Configuration

### Environment Variables

#### SMTP Configuration
```bash
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=alerts@mtbf-platform.com
SMTP_FROM_NAME=MTBF Platform Alerts
```

#### Webhook Configuration
```bash
WEBHOOK_TIMEOUT_SECONDS=30
WEBHOOK_RETRY_ATTEMPTS=3
WEBHOOK_RETRY_BACKOFF_SECONDS=5
```

### Supported Metrics

The system monitors KPI metrics computed by the scheduling system:

- **rolling**: Hourly rolling window KPIs for assets
- **calendar**: Daily calendar period KPIs for groups

### Threshold Comparators

- **gt**: Greater than threshold
- **gte**: Greater than or equal to threshold
- **lt**: Less than threshold
- **lte**: Less than or equal to threshold
- **eq**: Equal to threshold
- **ne**: Not equal to threshold

### Severity Levels

- **low**: Minor issues, informational
- **medium**: Moderate issues requiring attention
- **high**: Serious issues requiring immediate attention
- **critical**: Critical issues requiring emergency response

## Notification Channels

### Email Notifications

Email alerts include:
- Alert severity and status
- Policy name and description
- Current value vs threshold
- Asset/group information
- Timestamp and direct link to alert

**Email Template Example:**
```
Subject: [HIGH ALERT] CPU Usage Alert - Server-01

Alert Details:
- Policy: High CPU Usage
- Severity: High
- Status: Active
- Current Value: 95.2%
- Threshold: >90.0%
- Asset: Server-01
- Time: 2024-01-15 10:30:00 UTC

Description: Alert when CPU usage exceeds 90%

View Alert: https://mtbf-platform.com/alerts/events/{alert_id}
```

### Webhook Notifications

Webhook payloads are sent as JSON with HMAC signatures:

```json
{
  "alert_id": "alert-uuid",
  "policy_id": "policy-uuid",
  "policy_name": "High CPU Usage",
  "severity": "high",
  "status": "active",
  "message": "cpu_usage gt 90.0 (current: 95.2)",
  "current_value": 95.2,
  "threshold_value": 90.0,
  "asset_id": "asset-uuid",
  "group_id": null,
  "created_at": "2024-01-15T10:30:00Z"
}
```

**Signature Verification:**
If a webhook secret is configured, requests include an `X-Alert-Signature` header:

```python
import hmac
import hashlib

def verify_signature(payload, signature, secret):
    expected = hmac.new(
        secret.encode(),
        payload.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(f"sha256={expected}", signature)
```

## Deduplication

The system prevents alert fatigue through deduplication windows:

1. When an alert is triggered, the system checks for existing alerts
2. If an active alert exists for the same policy+asset within the deduplication window, no new alert is created
3. The deduplication window is configurable per policy (default: 60 minutes)
4. Deduplication is bypassed when:
   - No existing alert exists for the policy+asset combination
   - Existing alerts are resolved or older than the window

## Alert Lifecycle

1. **Triggered**: KPI value crosses policy threshold
2. **Active**: Alert is active and notifications sent
3. **Acknowledged**: User acknowledges the alert (optional)
4. **Resolved**: Alert is resolved by user or automatically

## Event Logging

All alert state changes are logged:

- **TRIGGERED**: Alert created due to threshold crossing
- **NOTIFIED**: Notifications sent successfully
- **ACKNOWLEDGED**: Alert acknowledged by user
- **RESOLVED**: Alert resolved by user

Events include:
- Timestamp
- User ID (for user actions)
- Message/description
- Optional metadata JSON

## Integration with KPI System

Alert evaluation is automatically triggered after KPI computation:

1. KPI snapshot is created for asset/group
2. Alert evaluation task is queued
3. All active policies for the metric type are evaluated
4. Alerts created for threshold crossings (subject to deduplication)
5. Notifications sent for new alerts

## Permissions

### Role-Based Access Control

- **Maintainer**: Full access to create, update, delete policies
- **Operator**: Can create and update policies, view alerts
- **Manager**: Read-only access to policies and alerts

### Required Permissions

- **Policy Management**: Maintainer, Operator
- **Policy Deletion**: Maintainer only
- **Alert Viewing**: All authenticated users
- **Alert Acknowledgment/Resolution**: All authenticated users

## Monitoring and Troubleshooting

### Health Checks

Monitor these metrics:
- Alert evaluation task success rate
- Notification delivery success/failure
- Active alert count by severity
- Deduplication effectiveness

### Common Issues

#### Alerts Not Triggering
- Check policy is active and matches metric name
- Verify threshold and comparator logic
- Check KPI snapshots are being created
- Review alert evaluation task logs

#### Notification Failures
- Verify SMTP/webhook configuration
- Check network connectivity
- Review notification service logs
- Validate webhook signature handling

#### Excessive Alerts
- Increase deduplication window
- Adjust thresholds to appropriate levels
- Review policy configuration
- Consider policy consolidation

### Logs

Key log locations:
- Alert evaluation: `worker.tasks.evaluate_alerts_task`
- Policy management: `app.services.AlertPolicyService`
- Notification delivery: `app.services.AlertNotificationService`
- API operations: FastAPI access logs

## Best Practices

### Policy Design
1. **Meaningful Names**: Use descriptive policy names
2. **Appropriate Thresholds**: Set thresholds based on historical data
3. **Severity Levels**: Match severity to business impact
4. **Deduplication**: Configure appropriate windows to prevent fatigue

### Notification Setup
1. **Redundant Channels**: Use both email and webhooks for critical alerts
2. **Clear Messages**: Include actionable information in notifications
3. **Webhook Security**: Always use webhook secrets
4. **Testing**: Test notification channels before production use

### Alert Management
1. **Regular Review**: Periodically review and update policies
2. **Documentation**: Document alert procedures and escalation paths
3. **Training**: Train teams on alert response procedures
4. **Automation**: Automate common resolution actions where possible