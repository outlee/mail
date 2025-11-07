import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Alert,
  Spin,
  Button,
  Drawer,
  Space,
  Tag,
  Breadcrumb,
} from 'antd'
import { ArrowLeftOutlined, AlertOutlined } from '@ant-design/icons'
import { dashboardAPI, AssetDetail, FailureEvent } from '../services/dashboardAPI'

interface SelectedFailure {
  visible: boolean
  data: FailureEvent | null
}

function AssetDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const [asset, setAsset] = useState<AssetDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selectedFailure, setSelectedFailure] = useState<SelectedFailure>({
    visible: false,
    data: null,
  })

  const loadAssetDetail = async () => {
    if (!id) return
    try {
      setLoading(true)
      const data = await dashboardAPI.getAssetDetail(id)
      setAsset(data)
      setError(null)
    } catch (err) {
      console.error('Failed to load asset:', err)
      setError('Failed to load asset details')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!id) return
    loadAssetDetail()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  if (loading) {
    return (
      <div style={{ textAlign: 'center', marginTop: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!asset) {
    return (
      <Alert
        message="Asset Not Found"
        description="The requested asset could not be found."
        type="error"
        showIcon
      />
    )
  }

  const failureColumns = [
    {
      title: 'Failure Mode',
      dataIndex: 'failure_mode',
      key: 'failure_mode',
      render: (text: string, record: FailureEvent) => (
        <Button type="link" onClick={() => setSelectedFailure({ visible: true, data: record })}>
          {text}
        </Button>
      ),
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => {
        const colors: { [key: string]: string } = {
          critical: 'red',
          high: 'orange',
          medium: 'yellow',
          low: 'green',
        }
        return <Tag color={colors[severity] || 'blue'}>{severity}</Tag>
      },
    },
    {
      title: 'Duration (mins)',
      dataIndex: 'duration_minutes',
      key: 'duration_minutes',
      render: (value?: number) => (value ? value.toFixed(2) : 'N/A'),
    },
    {
      title: 'Start Time',
      dataIndex: 'start_time',
      key: 'start_time',
      render: (date: string) => new Date(date).toLocaleString(),
    },
  ]

  const mtbfValue = asset.latest_kpi ? (asset.latest_kpi.value * 100).toFixed(2) : 'N/A'
  const failureCount = asset.recent_failures.length

  return (
    <div>
      <Breadcrumb style={{ marginBottom: '24px' }}>
        <Breadcrumb.Item>
          <Button type="link" icon={<ArrowLeftOutlined />} onClick={() => navigate('/dashboard')}>
            Overview
          </Button>
        </Breadcrumb.Item>
        <Breadcrumb.Item>{asset.name}</Breadcrumb.Item>
      </Breadcrumb>

      <h1>{asset.name}</h1>

      {error && (
        <Alert
          message="Load Error"
          description={error}
          type="error"
          showIcon
          closable
          style={{ marginBottom: '24px' }}
          onClose={() => setError(null)}
        />
      )}

      {asset.description && (
        <Card style={{ marginBottom: '24px' }}>
          <p>{asset.description}</p>
        </Card>
      )}

      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="Latest MTBF"
              value={mtbfValue}
              suffix="%"
              valueStyle={{
                color: asset.latest_kpi && asset.latest_kpi.value > 90 ? '#3f8600' : '#ff7a45',
              }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="Recent Failures"
              value={failureCount}
              prefix={<AlertOutlined />}
              valueStyle={{ color: failureCount > 5 ? '#cf1322' : '#faad14' }}
            />
          </Card>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Card>
            <Statistic
              title="Asset Status"
              value={asset.recent_failures.length === 0 ? 'Healthy' : 'Degraded'}
              valueStyle={{
                color: asset.recent_failures.length === 0 ? '#3f8600' : '#cf1322',
              }}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={[16, 16]}>
        <Col xs={24} lg={14}>
          <Card title="KPI Timeline">
            <div
              style={{
                height: '300px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                backgroundColor: '#fafafa',
                borderRadius: '4px',
              }}
            >
              <span style={{ color: '#999' }}>Timeline chart will display here</span>
            </div>
            {asset.latest_kpi && (
              <div style={{ marginTop: '12px', fontSize: '12px', color: '#666' }}>
                <p>Latest Update: {new Date(asset.latest_kpi.created_at).toLocaleString()}</p>
                <p>
                  Period: {new Date(asset.latest_kpi.period_start).toLocaleDateString()} to{' '}
                  {new Date(asset.latest_kpi.period_end).toLocaleDateString()}
                </p>
              </div>
            )}
          </Card>
        </Col>

        <Col xs={24} lg={10}>
          <Card title="Asset Information">
            <Space direction="vertical" style={{ width: '100%' }}>
              <div>
                <strong>Asset ID:</strong> {asset.id}
              </div>
              <div>
                <strong>Created:</strong> {new Date(asset.created_at).toLocaleString()}
              </div>
              <div>
                <strong>Last Updated:</strong> {new Date(asset.updated_at).toLocaleString()}
              </div>
              {asset.latest_kpi && (
                <>
                  <div>
                    <strong>KPI Type:</strong> {asset.latest_kpi.kpi_type}
                  </div>
                  <div>
                    <strong>Raw Value:</strong> {asset.latest_kpi.value.toFixed(4)}
                  </div>
                </>
              )}
            </Space>
          </Card>
        </Col>
      </Row>

      <Card title="Recent Failures" style={{ marginTop: '24px' }}>
        {failureCount === 0 ? (
          <p style={{ textAlign: 'center', color: '#999' }}>No recent failures recorded</p>
        ) : (
          <Table
            columns={failureColumns}
            dataSource={asset.recent_failures.map((f) => ({
              ...f,
              key: f.id,
            }))}
            pagination={false}
            size="small"
          />
        )}
      </Card>

      <Drawer
        title="Failure Details"
        onClose={() => setSelectedFailure({ visible: false, data: null })}
        open={selectedFailure.visible}
        width={400}
      >
        {selectedFailure.data && (
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <strong>Failure Mode:</strong> {selectedFailure.data.failure_mode}
            </div>
            <div>
              <strong>Severity:</strong> <Tag color="red">{selectedFailure.data.severity}</Tag>
            </div>
            {selectedFailure.data.failure_code && (
              <div>
                <strong>Failure Code:</strong> {selectedFailure.data.failure_code}
              </div>
            )}
            <div>
              <strong>Start Time:</strong>{' '}
              {new Date(selectedFailure.data.start_time).toLocaleString()}
            </div>
            {selectedFailure.data.end_time && (
              <div>
                <strong>End Time:</strong>{' '}
                {new Date(selectedFailure.data.end_time).toLocaleString()}
              </div>
            )}
            {selectedFailure.data.duration_minutes && (
              <div>
                <strong>Duration:</strong> {selectedFailure.data.duration_minutes.toFixed(2)}{' '}
                minutes
              </div>
            )}
            {selectedFailure.data.description && (
              <div>
                <strong>Description:</strong> {selectedFailure.data.description}
              </div>
            )}
          </Space>
        )}
      </Drawer>
    </div>
  )
}

export default AssetDetailPage
