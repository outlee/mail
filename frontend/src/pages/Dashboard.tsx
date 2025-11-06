import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Alert, Spin } from 'antd'
import { CheckCircleOutlined, ApiOutlined } from '@ant-design/icons'
import { apiClient } from '../services/api'

interface HealthStatus {
  status: string
}

function Dashboard() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const response = await apiClient.get<HealthStatus>('/health')
        setHealth(response.data)
        setError(null)
      } catch (err) {
        setError('Failed to connect to API')
        console.error('Health check failed:', err)
      } finally {
        setLoading(false)
      }
    }

    checkHealth()
  }, [])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', marginTop: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  return (
    <div>
      <h1>Dashboard</h1>

      {error && (
        <Alert
          message="API Connection Error"
          description={error}
          type="error"
          showIcon
          style={{ marginBottom: '24px' }}
        />
      )}

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="API Status"
              value={health?.status === 'ok' ? 'Healthy' : 'Unhealthy'}
              prefix={<CheckCircleOutlined />}
              valueStyle={{ color: health?.status === 'ok' ? '#3f8600' : '#cf1322' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="Platform"
              value="MTBF"
              prefix={<ApiOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic title="Version" value="0.1.0" />
          </Card>
        </Col>
      </Row>

      <Card title="Welcome" style={{ marginTop: '24px' }}>
        <p>
          Welcome to the MTBF Platform. This is a placeholder dashboard that demonstrates the
          integration between the React frontend and FastAPI backend.
        </p>
        <p>
          The backend health check is: <strong>{health?.status || 'unknown'}</strong>
        </p>
      </Card>
    </div>
  )
}

export default Dashboard
