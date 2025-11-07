import type {
  AlertPolicy,
  AlertEvent,
  AlertHistory,
  CreateAlertPolicyRequest,
  UpdateAlertPolicyRequest,
  AcknowledgeAlertRequest,
  AlertFilters,
} from '../types/alerts'

// Mock data for development
const mockPolicies: AlertPolicy[] = [
  {
    id: '1',
    name: 'High MTBF Alert',
    description: 'Alert when MTBF exceeds threshold',
    metric: 'mtbf',
    comparator: 'greater_than',
    threshold: 1000,
    cooldown_minutes: 60,
    severity: 'high',
    enabled: true,
    recipients: [
      {
        id: '1',
        type: 'email',
        email: 'admin@example.com',
        enabled: true,
      },
      {
        id: '2',
        type: 'webhook',
        url: 'https://hooks.slack.com/test',
        enabled: true,
      },
    ],
    created_at: '2024-01-15T10:30:00Z',
    updated_at: '2024-01-15T10:30:00Z',
    created_by: '1',
  },
  {
    id: '2',
    name: 'Low Availability Warning',
    description: 'Warning when availability drops below 95%',
    metric: 'availability',
    comparator: 'less_than',
    threshold: 95,
    cooldown_minutes: 30,
    severity: 'medium',
    enabled: true,
    recipients: [
      {
        id: '3',
        type: 'email',
        email: 'ops@example.com',
        enabled: true,
      },
    ],
    created_at: '2024-01-14T15:45:00Z',
    updated_at: '2024-01-14T15:45:00Z',
    created_by: '1',
  },
]

const mockAlerts: AlertEvent[] = [
  {
    id: '1',
    policy_id: '1',
    policy_name: 'High MTBF Alert',
    severity: 'high',
    status: 'active',
    message: 'MTBF value of 1200 exceeds threshold of 1000',
    metric_value: 1200,
    threshold: 1000,
    triggered_at: '2024-01-16T09:15:00Z',
    asset_id: 'asset-1',
    asset_name: 'Production Server A',
  },
  {
    id: '2',
    policy_id: '2',
    policy_name: 'Low Availability Warning',
    severity: 'medium',
    status: 'acknowledged',
    message: 'Availability dropped to 92.5%, below threshold of 95%',
    metric_value: 92.5,
    threshold: 95,
    triggered_at: '2024-01-16T08:30:00Z',
    acknowledged_at: '2024-01-16T09:00:00Z',
    acknowledged_by: 'user-1',
    asset_id: 'asset-2',
    asset_name: 'Database Server B',
  },
  {
    id: '3',
    policy_id: '1',
    policy_name: 'High MTBF Alert',
    severity: 'critical',
    status: 'resolved',
    message: 'Critical MTBF spike detected',
    metric_value: 1500,
    threshold: 1000,
    triggered_at: '2024-01-15T14:20:00Z',
    acknowledged_at: '2024-01-15T14:45:00Z',
    acknowledged_by: 'user-2',
    resolved_at: '2024-01-15T16:30:00Z',
    asset_id: 'asset-3',
    asset_name: 'Web Server C',
  },
]

const mockHistory: AlertHistory[] = [
  {
    id: '1',
    event_id: '1',
    action: 'triggered',
    message: 'Alert triggered by policy violation',
    timestamp: '2024-01-16T09:15:00Z',
  },
  {
    id: '2',
    event_id: '2',
    action: 'triggered',
    message: 'Alert triggered by policy violation',
    timestamp: '2024-01-16T08:30:00Z',
  },
  {
    id: '3',
    event_id: '2',
    action: 'acknowledged',
    message: 'Alert acknowledged by John Doe',
    user_id: 'user-1',
    user_name: 'John Doe',
    timestamp: '2024-01-16T09:00:00Z',
  },
]

// Simulate API delay
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms))

// Alert Policies API
export const alertsAPI = {
  // Get all alert policies
  getPolicies: async (): Promise<AlertPolicy[]> => {
    await delay(500)
    return [...mockPolicies]
  },

  // Get single alert policy
  getPolicy: async (id: string): Promise<AlertPolicy> => {
    await delay(300)
    const policy = mockPolicies.find((p) => p.id === id)
    if (!policy) {
      throw new Error('Policy not found')
    }
    return { ...policy }
  },

  // Create alert policy
  createPolicy: async (data: CreateAlertPolicyRequest): Promise<AlertPolicy> => {
    await delay(800)

    // Check for duplicate names
    if (mockPolicies.some((p) => p.name === data.name)) {
      throw new Error('Policy with this name already exists')
    }

    const newPolicy: AlertPolicy = {
      id: Date.now().toString(),
      ...data,
      enabled: true,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      created_by: 'current-user', // Would come from auth context
    }

    mockPolicies.push(newPolicy)
    return { ...newPolicy }
  },

  // Update alert policy
  updatePolicy: async (id: string, data: UpdateAlertPolicyRequest): Promise<AlertPolicy> => {
    await delay(800)

    const index = mockPolicies.findIndex((p) => p.id === id)
    if (index === -1) {
      throw new Error('Policy not found')
    }

    // Check for duplicate names (excluding current policy)
    if (data.name && mockPolicies.some((p) => p.id !== id && p.name === data.name)) {
      throw new Error('Policy with this name already exists')
    }

    mockPolicies[index] = {
      ...mockPolicies[index],
      ...data,
      updated_at: new Date().toISOString(),
    }

    return { ...mockPolicies[index] }
  },

  // Delete alert policy
  deletePolicy: async (id: string): Promise<void> => {
    await delay(500)

    const index = mockPolicies.findIndex((p) => p.id === id)
    if (index === -1) {
      throw new Error('Policy not found')
    }

    mockPolicies.splice(index, 1)
  },

  // Get alert events
  getAlerts: async (filters?: AlertFilters): Promise<AlertEvent[]> => {
    await delay(500)

    let filteredAlerts = [...mockAlerts]

    if (filters) {
      if (filters.status && filters.status.length > 0) {
        filteredAlerts = filteredAlerts.filter((a) => filters.status!.includes(a.status))
      }
      if (filters.severity && filters.severity.length > 0) {
        filteredAlerts = filteredAlerts.filter((a) => filters.severity!.includes(a.severity))
      }
      if (filters.policy_id) {
        filteredAlerts = filteredAlerts.filter((a) => a.policy_id === filters.policy_id)
      }
    }

    return filteredAlerts
  },

  // Get single alert event
  getAlert: async (id: string): Promise<AlertEvent> => {
    await delay(300)
    const alert = mockAlerts.find((a) => a.id === id)
    if (!alert) {
      throw new Error('Alert not found')
    }
    return { ...alert }
  },

  // Acknowledge alert
  acknowledgeAlert: async (id: string, data: AcknowledgeAlertRequest): Promise<AlertEvent> => {
    await delay(800)

    const alert = mockAlerts.find((a) => a.id === id)
    if (!alert) {
      throw new Error('Alert not found')
    }

    if (alert.status !== 'active') {
      throw new Error('Alert is not active')
    }

    alert.status = 'acknowledged'
    alert.acknowledged_at = new Date().toISOString()
    alert.acknowledged_by = 'current-user' // Would come from auth context

    // Add history entry
    mockHistory.push({
      id: Date.now().toString(),
      event_id: id,
      action: 'acknowledged',
      message: data.message || 'Alert acknowledged',
      user_id: 'current-user',
      user_name: 'Current User',
      timestamp: new Date().toISOString(),
    })

    return { ...alert }
  },

  // Bulk acknowledge alerts
  bulkAcknowledgeAlerts: async (ids: string[], data: AcknowledgeAlertRequest): Promise<void> => {
    await delay(1000)

    for (const id of ids) {
      const alert = mockAlerts.find((a) => a.id === id)
      if (alert && alert.status === 'active') {
        alert.status = 'acknowledged'
        alert.acknowledged_at = new Date().toISOString()
        alert.acknowledged_by = 'current-user'

        mockHistory.push({
          id: Date.now().toString() + Math.random(),
          event_id: id,
          action: 'acknowledged',
          message: data.message || 'Alert acknowledged',
          user_id: 'current-user',
          user_name: 'Current User',
          timestamp: new Date().toISOString(),
        })
      }
    }
  },

  // Get alert history
  getAlertHistory: async (alertId: string): Promise<AlertHistory[]> => {
    await delay(300)
    return mockHistory.filter((h) => h.event_id === alertId)
  },
}
