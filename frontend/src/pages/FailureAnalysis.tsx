import { useEffect, useState } from 'react'
import { Card, Row, Col, Table, Button, Alert, Spin, Space, Tag, Segmented } from 'antd'
import { DownloadOutlined, BarChartOutlined } from '@ant-design/icons'
import { dashboardAPI, FailureEvent, KPIStats } from '../services/dashboardAPI'

interface ParetoItem {
  failure_mode: string
  count: number
  percentage: number
  cumulative_percentage: number
}

function FailureAnalysis() {
  const [failures, setFailures] = useState<FailureEvent[]>([])
  const [stats, setStats] = useState<KPIStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [paretoData, setParetoData] = useState<ParetoItem[]>([])
  const [viewMode, setViewMode] = useState<'table' | 'pareto'>('pareto')

  useEffect(() => {
    loadFailureData()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const loadFailureData = async () => {
    try {
      setLoading(true)
      const [failuresList, statsData] = await Promise.all([
        dashboardAPI.getFailures(undefined, 0, 1000),
        dashboardAPI.getDashboardStats(),
      ])
      setFailures(failuresList)
      setStats(statsData)

      calculatePareto(statsData.failures_by_mode)
      setError(null)
    } catch (err) {
      console.error('Failed to load failures:', err)
      setError('Failed to load failure analysis data')
    } finally {
      setLoading(false)
    }
  }

  const calculatePareto = (failuresByMode: { [key: string]: number }) => {
    const total = Object.values(failuresByMode).reduce((a, b) => a + b, 0)
    const items: ParetoItem[] = Object.entries(failuresByMode)
      .map(([mode, count]) => ({
        failure_mode: mode,
        count,
        percentage: (count / total) * 100,
        cumulative_percentage: 0,
      }))
      .sort((a, b) => b.count - a.count)

    let cumulative = 0
    items.forEach((item) => {
      cumulative += item.percentage
      item.cumulative_percentage = cumulative
    })

    setParetoData(items)
  }

  const exportToCSV = () => {
    const headers = ['Failure Mode', 'Count', 'Percentage', 'Cumulative %']
    const rows = paretoData.map((item) => [
      item.failure_mode,
      item.count,
      item.percentage.toFixed(2),
      item.cumulative_percentage.toFixed(2),
    ])

    let csv = headers.join(',') + '\n'
    rows.forEach((row) => {
      csv += row.join(',') + '\n'
    })

    const element = document.createElement('a')
    element.setAttribute('href', 'data:text/csv;charset=utf-8,' + encodeURIComponent(csv))
    element.setAttribute('download', 'pareto-analysis.csv')
    element.style.display = 'none'
    document.body.appendChild(element)
    element.click()
    document.body.removeChild(element)
  }

  if (loading) {
    return (
      <div style={{ textAlign: 'center', marginTop: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  const paretoColumns = [
    {
      title: 'Failure Mode',
      dataIndex: 'failure_mode',
      key: 'failure_mode',
      width: '35%',
    },
    {
      title: 'Count',
      dataIndex: 'count',
      key: 'count',
      width: '15%',
      sorter: (a: ParetoItem, b: ParetoItem) => a.count - b.count,
    },
    {
      title: 'Percentage',
      dataIndex: 'percentage',
      key: 'percentage',
      width: '20%',
      render: (value: number) => {
        const color = value > 20 ? '#ff7a45' : value > 10 ? '#faad14' : '#3f8600'
        return <span style={{ color }}>{value.toFixed(2)}%</span>
      },
    },
    {
      title: 'Cumulative %',
      dataIndex: 'cumulative_percentage',
      key: 'cumulative_percentage',
      width: '20%',
      render: (value: number) => (
        <Tag color={value > 80 ? 'red' : value > 50 ? 'orange' : 'blue'}>{value.toFixed(2)}%</Tag>
      ),
    },
  ]

  return (
    <div>
      <div
        style={{
          marginBottom: '24px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
        }}
      >
        <h1>Failure Analysis - Pareto Chart</h1>
        <Space>
          <Segmented
            value={viewMode}
            onChange={(value) => setViewMode(value as 'table' | 'pareto')}
            options={[
              { label: 'Pareto View', value: 'pareto' },
              { label: 'Table View', value: 'table' },
            ]}
          />
          <Button
            icon={<DownloadOutlined />}
            onClick={exportToCSV}
            disabled={paretoData.length === 0}
          >
            Export CSV
          </Button>
        </Space>
      </div>

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

      <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
        <Col xs={24} sm={12} md={8}>
          <Card>
            <div style={{ fontSize: '14px', marginBottom: '8px' }}>Total Failure Modes</div>
            <div
              style={{
                fontSize: '32px',
                fontWeight: 'bold',
                color: '#1890ff',
              }}
            >
              {paretoData.length}
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Card>
            <div style={{ fontSize: '14px', marginBottom: '8px' }}>Total Failures</div>
            <div
              style={{
                fontSize: '32px',
                fontWeight: 'bold',
                color: '#ff7a45',
              }}
            >
              {stats?.total_failures || 0}
            </div>
          </Card>
        </Col>

        <Col xs={24} sm={12} md={8}>
          <Card>
            <div style={{ fontSize: '14px', marginBottom: '8px' }}>80/20 Rule Coverage</div>
            <div
              style={{
                fontSize: '32px',
                fontWeight: 'bold',
                color:
                  paretoData.length > 0 && paretoData[0].cumulative_percentage < 80
                    ? '#3f8600'
                    : '#faad14',
              }}
            >
              {paretoData.length > 0
                ? paretoData.findIndex((p) => p.cumulative_percentage >= 80) + 1
                : 0}{' '}
              modes
            </div>
          </Card>
        </Col>
      </Row>

      {viewMode === 'pareto' ? (
        <Card title="Pareto Analysis - Failure Modes by Impact">
          <div style={{ overflowX: 'auto' }}>
            {paretoData.length === 0 ? (
              <div
                style={{
                  textAlign: 'center',
                  padding: '40px',
                  backgroundColor: '#fafafa',
                }}
              >
                <BarChartOutlined
                  style={{
                    fontSize: '48px',
                    color: '#999',
                    marginBottom: '16px',
                  }}
                />
                <p style={{ color: '#999' }}>No failure data available yet</p>
              </div>
            ) : (
              <div>
                {paretoData.map((item, index) => (
                  <div key={item.failure_mode} style={{ marginBottom: '16px' }}>
                    <div
                      style={{
                        display: 'flex',
                        justifyContent: 'space-between',
                        marginBottom: '4px',
                      }}
                    >
                      <strong>
                        {index + 1}. {item.failure_mode}
                      </strong>
                      <span>
                        {item.count} failures ({item.percentage.toFixed(2)}%)
                      </span>
                    </div>
                    <div style={{ position: 'relative', height: '20px' }}>
                      <div
                        style={{
                          position: 'absolute',
                          height: '100%',
                          backgroundColor:
                            item.cumulative_percentage >= 80
                              ? '#ff7a45'
                              : item.cumulative_percentage >= 50
                                ? '#faad14'
                                : '#1890ff',
                          width: `${Math.min((item.cumulative_percentage / 100) * 100, 100)}%`,
                          borderRadius: '2px',
                        }}
                      />
                      <span
                        style={{
                          position: 'absolute',
                          right: '8px',
                          top: '50%',
                          transform: 'translateY(-50%)',
                          fontSize: '12px',
                          fontWeight: 'bold',
                          color: item.cumulative_percentage >= 80 ? '#fff' : '#666',
                        }}
                      >
                        {item.cumulative_percentage.toFixed(1)}%
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
          <div style={{ marginTop: '24px', fontSize: '12px', color: '#666' }}>
            <p>
              <strong>80/20 Rule Insight:</strong> Typically, 80% of failures are caused by 20% of
              the failure modes. This chart helps identify which failure modes have the highest
              impact.
            </p>
          </div>
        </Card>
      ) : (
        <Card title="Failure Modes Details">
          <Table
            columns={paretoColumns}
            dataSource={paretoData.map((item) => ({
              ...item,
              key: item.failure_mode,
            }))}
            pagination={false}
            size="small"
          />
        </Card>
      )}

      <Card title="Filtered Failures" style={{ marginTop: '24px' }}>
        <Table
          columns={[
            {
              title: 'Failure Mode',
              dataIndex: 'failure_mode',
              key: 'failure_mode',
            },
            {
              title: 'Asset ID',
              dataIndex: 'asset_id',
              key: 'asset_id',
              width: '20%',
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
              title: 'Start Time',
              dataIndex: 'start_time',
              key: 'start_time',
              render: (date: string) => new Date(date).toLocaleString(),
              width: '20%',
            },
          ]}
          dataSource={failures.slice(0, 20).map((f) => ({
            ...f,
            key: f.id,
          }))}
          pagination={{ pageSize: 20, total: failures.length }}
          size="small"
        />
      </Card>
    </div>
  )
}

export default FailureAnalysis
