import { useEffect, useState } from 'react'
import { Card, Row, Col, Statistic, Alert, Spin, Table, Button, Space, Tag, Select } from 'antd'
import { ThunderboltOutlined, AlertOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { dashboardAPI, KPIStats, AssetSummary } from '../services/dashboardAPI'

interface WindowOption {
  label: string
  value: string
}

const windowOptions: WindowOption[] = [
  { label: 'Last 24 Hours', value: '24h' },
  { label: 'Last 7 Days', value: '7d' },
  { label: 'Last 30 Days', value: '30d' },
  { label: 'All Time', value: 'all' },
]

function Overview() {
  const [stats, setStats] = useState<KPIStats | null>(null)
  const [topAssets, setTopAssets] = useState<AssetSummary[]>([])
  const [bottomAssets, setBottomAssets] = useState<AssetSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [window, setWindow] = useState('24h')
  const navigate = useNavigate()

  useEffect(() => {
    loadDashboardData()
  }, [window])

  const loadDashboardData = async () => {
    try {
      setLoading(true)
      const [statsData, top, bottom] = await Promise.all([
        dashboardAPI.getDashboardStats(),
        dashboardAPI.getTopAssets(10),
        dashboardAPI.getBottomAssets(10),
      ])
      setStats(statsData)
      setTopAssets(top)
      setBottomAssets(bottom)
      setError(null)
    } catch (err) {
      console.error('Failed to load dashboard:', err)
      setError('Failed to load dashboard data')
    } finally {
      setLoading(false)
    }
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', marginTop: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  const topAssetsColumns = [
    {
      title: 'Asset Name',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: AssetSummary) => (
        <Button type="link" onClick={() => navigate(`/assets/${record.id}`)}>
          {text}
        </Button>
      ),
    },
    {
      title: 'Avg KPI',
      dataIndex: 'avg_kpi',
      key: 'avg_kpi',
      render: (value: number) => value.toFixed(2),
    },
    {
      title: 'Failures',
      dataIndex: 'failure_count',
      key: 'failure_count',
    },
  ]

  const bottomAssetsColumns = [
    {
      title: 'Asset Name',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: AssetSummary) => (
        <Button type="link" onClick={() => navigate(`/assets/${record.id}`)}>
          {text}
        </Button>
      ),
    },
    {
      title: 'Avg KPI',
      dataIndex: 'avg_kpi',
      key: 'avg_kpi',
      render: (value: number) => <span style={{ color: '#cf1322' }}>{value.toFixed(2)}</span>,
    },
    {
      title: 'Failures',
      dataIndex: 'failure_count',
      key: 'failure_count',
      render: (value: number) => <Tag color={value > 5 ? 'red' : 'orange'}>{value}</Tag>,
    },
  ]

  return (
    <div>
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between' }}>
        <h1>Dashboard Overview</h1>
        <Select
          value={window}
          onChange={setWindow}
          options={windowOptions}
          style={{ width: '200px' }}
        />
      </div>

      {error && (
        <Alert
          message="Data Load Error"
          description={error}
          type="error"
          showIcon
          closable
          style={{ marginBottom: '24px' }}
          onClose={() => setError(null)}
        />
      )}

      <Row gutter={[16, 16]}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Average KPI"
              value={stats?.average_kpi || 0}
              precision={2}
              suffix="%"
              prefix={<ThunderboltOutlined />}
              valueStyle={{ color: '#1890ff' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Min KPI"
              value={stats?.min_kpi || 0}
              precision={2}
              suffix="%"
              valueStyle={{ color: '#cf1322' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Max KPI"
              value={stats?.max_kpi || 0}
              precision={2}
              suffix="%"
              valueStyle={{ color: '#3f8600' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Assets"
              value={stats?.total_assets || 0}
              valueStyle={{ color: '#722ed1' }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: '24px' }}>
        <Col xs={24} sm={12} md={6}>
          <Card>
            <Statistic
              title="Total Failures"
              value={stats?.total_failures || 0}
              prefix={<AlertOutlined />}
              valueStyle={{ color: '#ff7a45' }}
            />
          </Card>
        </Col>

        {stats?.failures_by_mode && Object.keys(stats.failures_by_mode).length > 0 && (
          <Col xs={24} sm={12} md={18}>
            <Card title="Failure Modes Summary">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px' }}>
                {Object.entries(stats.failures_by_mode).map(([mode, count]) => (
                  <Tag key={mode} color="blue">
                    {mode}: {count}
                  </Tag>
                ))}
              </div>
            </Card>
          </Col>
        )}
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: '24px' }}>
        <Col xs={24} lg={12}>
          <Card
            title="Top Performing Assets"
            extra={<Button onClick={() => navigate('/failure-analysis')}>View Analysis</Button>}
          >
            <Table
              columns={topAssetsColumns}
              dataSource={topAssets.map((asset) => ({ ...asset, key: asset.id }))}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>

        <Col xs={24} lg={12}>
          <Card
            title="Bottom Performing Assets"
            extra={<AlertOutlined style={{ color: '#ff7a45', fontSize: '18px' }} />}
          >
            <Table
              columns={bottomAssetsColumns}
              dataSource={bottomAssets.map((asset) => ({ ...asset, key: asset.id }))}
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]} style={{ marginTop: '24px' }}>
        <Col xs={24}>
          <Card title="Alert Summary">
            <div style={{ textAlign: 'center', padding: '20px' }}>
              <p>
                <Space>
                  <span>
                    Active Alerts: <strong>0</strong>
                  </span>
                  <span style={{ color: '#999' }}>•</span>
                  <span>
                    Acknowledged: <strong>0</strong>
                  </span>
                  <span style={{ color: '#999' }}>•</span>
                  <span>
                    Resolved Today: <strong>0</strong>
                  </span>
                </Space>
              </p>
              <p style={{ fontSize: '12px', color: '#999', marginTop: '12px' }}>
                Real-time alert integration coming soon
              </p>
            </div>
          </Card>
        </Col>
      </Row>
    </div>
  )
}

export default Overview
