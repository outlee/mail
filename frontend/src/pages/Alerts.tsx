import { useEffect, useState } from 'react'
import {
  Table,
  Button,
  Space,
  Tag,
  Card,
  Typography,
  Row,
  Col,
  Select,
  DatePicker,
  Modal,
  Timeline,
  message,
  Popconfirm,
  Badge,
} from 'antd'
import {
  CheckOutlined,
  EyeOutlined,
  FilterOutlined,
  BellOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import dayjs from 'dayjs'
import { alertsAPI } from '../services/alertsAPI'
import { authAPI } from '../services/api'
import type { AlertEvent, AlertHistory, AlertFilters } from '../types/alerts'
import { SEVERITY_OPTIONS, STATUS_OPTIONS } from '../types/alerts'

const { Title, Text } = Typography
const { RangePicker } = DatePicker

function Alerts() {
  const [alerts, setAlerts] = useState<AlertEvent[]>([])
  const [loading, setLoading] = useState(false)
  const [selectedRowKeys, setSelectedRowKeys] = useState<React.Key[]>([])
  const [detailModalVisible, setDetailModalVisible] = useState(false)
  const [selectedAlert, setSelectedAlert] = useState<AlertEvent | null>(null)
  const [alertHistory, setAlertHistory] = useState<AlertHistory[]>([])
  const [filters, setFilters] = useState<AlertFilters>({})
  const [filterPanelVisible, setFilterPanelVisible] = useState(false)
  const [userRole, setUserRole] = useState<string>('operator')

  useEffect(() => {
    const loadUserRole = async () => {
      try {
        const user = await authAPI.me()
        setUserRole(user.role)
      } catch (error) {
        console.error('Failed to load user role:', error)
      }
    }
    loadUserRole()
  }, [])

  const isReadonly = userRole === 'operator'

  useEffect(() => {
    loadAlerts()
  }, [filters]) // eslint-disable-line react-hooks/exhaustive-deps

  const loadAlerts = async () => {
    setLoading(true)
    try {
      const data = await alertsAPI.getAlerts(filters)
      setAlerts(data)
    } catch (error) {
      message.error('Failed to load alerts')
    } finally {
      setLoading(false)
    }
  }

  const handleViewDetail = async (alert: AlertEvent) => {
    setSelectedAlert(alert)
    try {
      const history = await alertsAPI.getAlertHistory(alert.id)
      setAlertHistory(history)
    } catch (error) {
      message.error('Failed to load alert history')
    }
    setDetailModalVisible(true)
  }

  const handleAcknowledge = async (alertId: string) => {
    try {
      await alertsAPI.acknowledgeAlert(alertId, { message: 'Alert acknowledged' })
      message.success('Alert acknowledged successfully')
      loadAlerts()
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to acknowledge alert'
      message.error(errorMessage)
    }
  }

  const handleBulkAcknowledge = async () => {
    if (selectedRowKeys.length === 0) {
      message.warning('Please select alerts to acknowledge')
      return
    }

    try {
      await alertsAPI.bulkAcknowledgeAlerts(selectedRowKeys as string[], {
        message: 'Bulk acknowledged',
      })
      message.success(`${selectedRowKeys.length} alerts acknowledged successfully`)
      setSelectedRowKeys([])
      loadAlerts()
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to acknowledge alerts'
      message.error(errorMessage)
    }
  }

  const handleFilterChange = (newFilters: Partial<AlertFilters>) => {
    setFilters((prev) => ({ ...prev, ...newFilters }))
  }

  const clearFilters = () => {
    setFilters({})
    setSelectedRowKeys([])
  }

  const getSeverityColor = (severity: string) => {
    const option = SEVERITY_OPTIONS.find((opt) => opt.value === severity)
    return option?.color || '#default'
  }

  const columns: ColumnsType<AlertEvent> = [
    {
      title: 'Alert',
      dataIndex: 'policy_name',
      key: 'policy_name',
      render: (text: string, record: AlertEvent) => (
        <Space direction="vertical" size={0}>
          <Text strong>{text}</Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {record.asset_name}
          </Text>
        </Space>
      ),
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)}>{severity.toUpperCase()}</Tag>
      ),
      filters: SEVERITY_OPTIONS.map((option) => ({
        text: option.label,
        value: option.value,
      })),
      onFilter: (value, record) => record.severity === value,
    },
    {
      title: 'Status',
      dataIndex: 'status',
      key: 'status',
      render: (status: string) => (
        <Badge
          status={status === 'active' ? 'error' : status === 'acknowledged' ? 'warning' : 'success'}
          text={status.toUpperCase()}
        />
      ),
      filters: STATUS_OPTIONS.map((option) => ({
        text: option.label,
        value: option.value,
      })),
      onFilter: (value, record) => record.status === value,
    },
    {
      title: 'Message',
      dataIndex: 'message',
      key: 'message',
      ellipsis: true,
    },
    {
      title: 'Metric Value',
      key: 'metric_value',
      render: (record: AlertEvent) => (
        <Space>
          <Text strong>{record.metric_value}</Text>
          <Text type="secondary">/ {record.threshold}</Text>
        </Space>
      ),
    },
    {
      title: 'Triggered',
      dataIndex: 'triggered_at',
      key: 'triggered_at',
      render: (date: string) => (
        <Space direction="vertical" size={0}>
          <Text>{dayjs(date).format('MMM DD, YYYY')}</Text>
          <Text type="secondary" style={{ fontSize: '12px' }}>
            {dayjs(date).format('HH:mm:ss')}
          </Text>
        </Space>
      ),
      sorter: (a, b) => dayjs(a.triggered_at).unix() - dayjs(b.triggered_at).unix(),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (record: AlertEvent) => (
        <Space>
          <Button type="link" icon={<EyeOutlined />} onClick={() => handleViewDetail(record)}>
            View
          </Button>
          {record.status === 'active' && !isReadonly && (
            <Popconfirm
              title="Acknowledge this alert?"
              onConfirm={() => handleAcknowledge(record.id)}
            >
              <Button type="link" icon={<CheckOutlined />}>
                Acknowledge
              </Button>
            </Popconfirm>
          )}
        </Space>
      ),
    },
  ]

  const rowSelection = {
    selectedRowKeys,
    onChange: (newSelectedRowKeys: React.Key[]) => {
      setSelectedRowKeys(newSelectedRowKeys)
    },
    getCheckboxProps: (record: AlertEvent) => ({
      disabled: record.status !== 'active' || isReadonly,
    }),
  }

  const activeAlertsCount = alerts.filter((a) => a.status === 'active').length
  const selectedActiveAlerts = selectedRowKeys.filter((key) => {
    const alert = alerts.find((a) => a.id === key)
    return alert?.status === 'active'
  })

  return (
    <div>
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          marginBottom: 24,
        }}
      >
        <Title level={2}>
          <Space>
            <BellOutlined />
            Alerts
            {activeAlertsCount > 0 && <Badge count={activeAlertsCount} size="small" />}
          </Space>
        </Title>
        <Space>
          {!isReadonly && selectedActiveAlerts.length > 0 && (
            <Popconfirm
              title={`Acknowledge ${selectedActiveAlerts.length} selected alerts?`}
              onConfirm={handleBulkAcknowledge}
            >
              <Button type="primary" icon={<CheckOutlined />}>
                Acknowledge Selected ({selectedActiveAlerts.length})
              </Button>
            </Popconfirm>
          )}
          <Button
            icon={<FilterOutlined />}
            onClick={() => setFilterPanelVisible(!filterPanelVisible)}
          >
            Filters
          </Button>
        </Space>
      </div>

      {filterPanelVisible && (
        <Card style={{ marginBottom: 24 }}>
          <Row gutter={16}>
            <Col span={6}>
              <Text strong>Status</Text>
              <Select
                mode="multiple"
                placeholder="Select status"
                style={{ width: '100%', marginTop: 8 }}
                value={filters.status}
                onChange={(value) => handleFilterChange({ status: value })}
                allowClear
              >
                {STATUS_OPTIONS.map((option) => (
                  <Select.Option key={option.value} value={option.value}>
                    {option.label}
                  </Select.Option>
                ))}
              </Select>
            </Col>
            <Col span={6}>
              <Text strong>Severity</Text>
              <Select
                mode="multiple"
                placeholder="Select severity"
                style={{ width: '100%', marginTop: 8 }}
                value={filters.severity}
                onChange={(value) => handleFilterChange({ severity: value })}
                allowClear
              >
                {SEVERITY_OPTIONS.map((option) => (
                  <Select.Option key={option.value} value={option.value}>
                    {option.label}
                  </Select.Option>
                ))}
              </Select>
            </Col>
            <Col span={8}>
              <Text strong>Date Range</Text>
              <RangePicker
                style={{ width: '100%', marginTop: 8 }}
                value={[
                  filters.date_from ? dayjs(filters.date_from) : null,
                  filters.date_to ? dayjs(filters.date_to) : null,
                ]}
                onChange={(dates) => {
                  handleFilterChange({
                    date_from: dates?.[0]?.toISOString(),
                    date_to: dates?.[1]?.toISOString(),
                  })
                }}
              />
            </Col>
            <Col span={4}>
              <Text strong>&nbsp;</Text>
              <div style={{ marginTop: 8 }}>
                <Button onClick={clearFilters}>Clear All</Button>
              </div>
            </Col>
          </Row>
        </Card>
      )}

      <Table
        columns={columns}
        dataSource={alerts}
        loading={loading}
        rowKey="id"
        rowSelection={isReadonly ? undefined : rowSelection}
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showTotal: (total, range) => `${range[0]}-${range[1]} of ${total} alerts`,
        }}
        scroll={{ x: 1000 }}
      />

      <Modal
        title="Alert Details"
        open={detailModalVisible}
        onCancel={() => setDetailModalVisible(false)}
        footer={[
          <Button key="close" onClick={() => setDetailModalVisible(false)}>
            Close
          </Button>,
          selectedAlert?.status === 'active' && !isReadonly && (
            <Popconfirm
              key="acknowledge"
              title="Acknowledge this alert?"
              onConfirm={() => {
                if (selectedAlert) {
                  handleAcknowledge(selectedAlert.id)
                  setDetailModalVisible(false)
                }
              }}
            >
              <Button type="primary" icon={<CheckOutlined />}>
                Acknowledge
              </Button>
            </Popconfirm>
          ),
        ]}
        width={800}
      >
        {selectedAlert && (
          <div>
            <Row gutter={16} style={{ marginBottom: 24 }}>
              <Col span={12}>
                <Card size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <Text type="secondary">Policy</Text>
                      <div>
                        <Text strong>{selectedAlert.policy_name}</Text>
                      </div>
                    </div>
                    <div>
                      <Text type="secondary">Asset</Text>
                      <div>
                        <Text>{selectedAlert.asset_name || 'N/A'}</Text>
                      </div>
                    </div>
                    <div>
                      <Text type="secondary">Severity</Text>
                      <div>
                        <Tag color={getSeverityColor(selectedAlert.severity)}>
                          {selectedAlert.severity.toUpperCase()}
                        </Tag>
                      </div>
                    </div>
                  </Space>
                </Card>
              </Col>
              <Col span={12}>
                <Card size="small">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div>
                      <Text type="secondary">Status</Text>
                      <div>
                        <Badge
                          status={
                            selectedAlert.status === 'active'
                              ? 'error'
                              : selectedAlert.status === 'acknowledged'
                                ? 'warning'
                                : 'success'
                          }
                          text={selectedAlert.status.toUpperCase()}
                        />
                      </div>
                    </div>
                    <div>
                      <Text type="secondary">Metric Value</Text>
                      <div>
                        <Text strong>{selectedAlert.metric_value}</Text>
                        <Text type="secondary"> / {selectedAlert.threshold}</Text>
                      </div>
                    </div>
                    <div>
                      <Text type="secondary">Triggered</Text>
                      <div>
                        <Text>
                          {dayjs(selectedAlert.triggered_at).format('MMM DD, YYYY HH:mm:ss')}
                        </Text>
                      </div>
                    </div>
                  </Space>
                </Card>
              </Col>
            </Row>

            <Card title="Message" size="small" style={{ marginBottom: 24 }}>
              <Text>{selectedAlert.message}</Text>
            </Card>

            {selectedAlert.acknowledged_at && (
              <Card title="Acknowledgment" size="small" style={{ marginBottom: 24 }}>
                <Space direction="vertical">
                  <Text>Acknowledged by: {selectedAlert.acknowledged_by || 'Unknown'}</Text>
                  <Text>
                    Acknowledged at:{' '}
                    {dayjs(selectedAlert.acknowledged_at).format('MMM DD, YYYY HH:mm:ss')}
                  </Text>
                </Space>
              </Card>
            )}

            <Card title="History Timeline" size="small">
              <Timeline>
                {alertHistory.map((item) => (
                  <Timeline.Item
                    key={item.id}
                    color={
                      item.action === 'triggered'
                        ? 'red'
                        : item.action === 'acknowledged'
                          ? 'orange'
                          : 'green'
                    }
                    dot={<ClockCircleOutlined />}
                  >
                    <Space direction="vertical" size={0}>
                      <Text strong>{item.action.toUpperCase()}</Text>
                      <Text>{item.message}</Text>
                      <Text type="secondary" style={{ fontSize: '12px' }}>
                        {item.user_name && `By ${item.user_name} • `}
                        {dayjs(item.timestamp).format('MMM DD, YYYY HH:mm:ss')}
                      </Text>
                    </Space>
                  </Timeline.Item>
                ))}
              </Timeline>
            </Card>
          </div>
        )}
      </Modal>
    </div>
  )
}

export default Alerts
