export type AlertSeverity = 'low' | 'medium' | 'high' | 'critical'

export type Comparator = 'greater_than' | 'less_than' | 'equals' | 'not_equals'

export type RecipientType = 'email' | 'webhook'

export type AlertStatus = 'active' | 'acknowledged' | 'resolved'

export interface EmailRecipient {
  id: string
  type: 'email'
  email: string
  enabled: boolean
}

export interface WebhookRecipient {
  id: string
  type: 'webhook'
  url: string
  secret?: string
  enabled: boolean
}

export type Recipient = EmailRecipient | WebhookRecipient

export interface AlertPolicy {
  id: string
  name: string
  description?: string
  metric: string
  comparator: Comparator
  threshold: number
  cooldown_minutes: number
  severity: AlertSeverity
  enabled: boolean
  recipients: Recipient[]
  created_at: string
  updated_at: string
  created_by: string
}

export interface AlertEvent {
  id: string
  policy_id: string
  policy_name: string
  severity: AlertSeverity
  status: AlertStatus
  message: string
  metric_value: number
  threshold: number
  triggered_at: string
  acknowledged_at?: string
  acknowledged_by?: string
  resolved_at?: string
  asset_id?: string
  asset_name?: string
}

export interface AlertHistory {
  id: string
  event_id: string
  action: 'triggered' | 'acknowledged' | 'resolved' | 'escalated'
  message: string
  user_id?: string
  user_name?: string
  timestamp: string
}

export interface CreateAlertPolicyRequest {
  name: string
  description?: string
  metric: string
  comparator: Comparator
  threshold: number
  cooldown_minutes: number
  severity: AlertSeverity
  recipients: Recipient[]
}

export interface UpdateAlertPolicyRequest extends Partial<CreateAlertPolicyRequest> {
  enabled?: boolean
}

export interface AcknowledgeAlertRequest {
  message?: string
}

export interface AlertFilters {
  status?: AlertStatus[]
  severity?: AlertSeverity[]
  policy_id?: string
  date_from?: string
  date_to?: string
}

// Available metrics for alert policies
export const AVAILABLE_METRICS = [
  { value: 'mtbf', label: 'Mean Time Between Failures' },
  { value: 'mttr', label: 'Mean Time To Repair' },
  { value: 'availability', label: 'Availability (%)' },
  { value: 'failure_rate', label: 'Failure Rate' },
  { value: 'uptime', label: 'Uptime (%)' },
  { value: 'downtime', label: 'Downtime (hours)' },
]

// Comparator options
export const COMPARATOR_OPTIONS = [
  { value: 'greater_than', label: 'Greater than' },
  { value: 'less_than', label: 'Less than' },
  { value: 'equals', label: 'Equals' },
  { value: 'not_equals', label: 'Not equals' },
]

// Severity options
export const SEVERITY_OPTIONS = [
  { value: 'low', label: 'Low', color: '#52c41a' },
  { value: 'medium', label: 'Medium', color: '#faad14' },
  { value: 'high', label: 'High', color: '#ff7a45' },
  { value: 'critical', label: 'Critical', color: '#ff4d4f' },
]

// Status options
export const STATUS_OPTIONS = [
  { value: 'active', label: 'Active', color: '#ff4d4f' },
  { value: 'acknowledged', label: 'Acknowledged', color: '#faad14' },
  { value: 'resolved', label: 'Resolved', color: '#52c41a' },
]
