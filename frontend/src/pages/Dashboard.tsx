import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Alert, Spin, Button } from 'antd'
import { CheckCircleOutlined, ApiOutlined, UserOutlined, BellOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { apiClient, authAPI, UserInfo } from '../services/api'

interface HealthStatus {
  status: string
}

function Dashboard() {
  const [health, setHealth] = useState<HealthStatus | null>(null)
  const [user, setUser] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const checkDashboard = async () => {
      try {
        const [healthResponse, userData] = await Promise.all([
          apiClient.get<HealthStatus>('/health'),
          authAPI.me(),
        ])
        setHealth(healthResponse.data)
        setUser(userData)
        setError(null)
      } catch (err) {
        setError('Failed to load dashboard')
        console.error('Dashboard load failed:', err)
      } finally {
        setLoading(false)
      }
    }

    checkDashboard()
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
              valueStyle={{
                color: health?.status === 'ok' ? '#3f8600' : '#cf1322',
              }}
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

      <Row gutter={[16, 16]} style={{ marginTop: '24px' }}>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="User"
              value={user?.full_name || 'Unknown'}
              prefix={<UserOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="Role"
              value={user?.role || 'unknown'}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="Email"
              value={user?.email || 'unknown'}
              valueStyle={{ color: '#13c2c2' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: '24px' }}>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <div style={{ cursor: 'pointer' }} onClick={() => navigate('/overview')}>
              <Statistic
                title="Dashboard"
                value="View"
                prefix={<BellOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </div>
            <div style={{ marginTop: '12px' }}>
              <Button type="primary" block onClick={() => navigate('/overview')}>
                Go to Overview
              </Button>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Card>
            <div style={{ cursor: 'pointer' }} onClick={() => navigate('/failure-analysis')}>
              <Statistic
                title="Failure Analysis"
                value="Analyze"
                prefix={<BellOutlined />}
                valueStyle={{ color: '#ff7a45' }}
              />
            </div>
            <div style={{ marginTop: '12px' }}>
              <Button type="primary" block onClick={() => navigate('/failure-analysis')}>
                View Analysis
              </Button>
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Card>
            <div style={{ cursor: 'pointer' }} onClick={() => navigate('/alerts')}>
              <Statistic
                title="Alerts Management"
                value="Manage"
                prefix={<BellOutlined />}
                valueStyle={{ color: '#1890ff' }}
              />
            </div>
            <div style={{ marginTop: '12px' }}>
              <Button type="primary" block onClick={() => navigate('/alerts')}>
                View Alerts
              </Button>
            </div>
          </Card>
        </Col>
      </Row>

      <Card title="Welcome" style={{ marginTop: '24px' }}>
        <p>
          Welcome to the MTBF Platform. This is a dashboard that demonstrates the authentication and
          integration between the React frontend and FastAPI backend.
        </p>
        <p>
          The backend health check is: <strong>{health?.status || 'unknown'}</strong>
        </p>
        {user && (
          <p>
            You are logged in as: <strong>{user.full_name}</strong> with role{' '}
            <strong>{user.role}</strong>
          </p>
        )}
      </Card>
    </div>
  )
}

export default Dashboard
