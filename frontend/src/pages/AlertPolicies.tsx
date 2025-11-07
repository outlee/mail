import { useEffect, useState } from 'react'
import {
  Table,
  Button,
  Space,
  Tag,
  Switch,
  Drawer,
  Form,
  Input,
  Select,
  InputNumber,
  message,
  Popconfirm,
  Card,
  Typography,
  Row,
  Col,
} from 'antd'
import {
  PlusOutlined,
  EditOutlined,
  DeleteOutlined,
  MailOutlined,
  LinkOutlined,
} from '@ant-design/icons'
import { alertsAPI } from '../services/alertsAPI'
import { authAPI } from '../services/api'
import type {
  AlertPolicy,
  CreateAlertPolicyRequest,
  UpdateAlertPolicyRequest,
  EmailRecipient,
} from '../types/alerts'
import { AVAILABLE_METRICS, COMPARATOR_OPTIONS, SEVERITY_OPTIONS } from '../types/alerts'

const { Title, Text } = Typography
const { Option } = Select

function AlertPolicies() {
  const [policies, setPolicies] = useState<AlertPolicy[]>([])
  const [loading, setLoading] = useState(false)
  const [drawerVisible, setDrawerVisible] = useState(false)
  const [editingPolicy, setEditingPolicy] = useState<AlertPolicy | null>(null)
  const [form] = Form.useForm()
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
    loadPolicies()
  }, [])

  const loadPolicies = async () => {
    setLoading(true)
    try {
      const data = await alertsAPI.getPolicies()
      setPolicies(data)
    } catch (error) {
      message.error('Failed to load alert policies')
    } finally {
      setLoading(false)
    }
  }

  const handleCreate = () => {
    setEditingPolicy(null)
    form.resetFields()
    form.setFieldsValue({
      recipients: [{ type: 'email', email: '', enabled: true }],
    })
    setDrawerVisible(true)
  }

  const handleEdit = (policy: AlertPolicy) => {
    setEditingPolicy(policy)
    form.setFieldsValue(policy)
    setDrawerVisible(true)
  }

  const handleDelete = async (id: string) => {
    try {
      await alertsAPI.deletePolicy(id)
      message.success('Policy deleted successfully')
      loadPolicies()
    } catch (error) {
      message.error('Failed to delete policy')
    }
  }

  const handleToggle = async (id: string, enabled: boolean) => {
    try {
      await alertsAPI.updatePolicy(id, { enabled })
      message.success(`Policy ${enabled ? 'enabled' : 'disabled'} successfully`)
      loadPolicies()
    } catch (error) {
      message.error('Failed to update policy status')
    }
  }

  const handleSubmit = async (values: CreateAlertPolicyRequest | UpdateAlertPolicyRequest) => {
    try {
      if (editingPolicy) {
        await alertsAPI.updatePolicy(editingPolicy.id, values as UpdateAlertPolicyRequest)
        message.success('Policy updated successfully')
      } else {
        await alertsAPI.createPolicy(values as CreateAlertPolicyRequest)
        message.success('Policy created successfully')
      }
      setDrawerVisible(false)
      loadPolicies()
    } catch (error: unknown) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save policy'
      message.error(errorMessage)
    }
  }

  const getSeverityColor = (severity: string) => {
    const option = SEVERITY_OPTIONS.find((opt) => opt.value === severity)
    return option?.color || '#default'
  }

  const columns = [
    {
      title: 'Name',
      dataIndex: 'name',
      key: 'name',
      render: (text: string, record: AlertPolicy) => (
        <Space>
          <Text strong>{text}</Text>
          {record.description && (
            <Text type="secondary" style={{ fontSize: '12px' }}>
              {record.description}
            </Text>
          )}
        </Space>
      ),
    },
    {
      title: 'Metric',
      dataIndex: 'metric',
      key: 'metric',
      render: (metric: string) => {
        const metricOption = AVAILABLE_METRICS.find((m) => m.value === metric)
        return metricOption?.label || metric
      },
    },
    {
      title: 'Condition',
      key: 'condition',
      render: (record: AlertPolicy) => {
        const comparator = COMPARATOR_OPTIONS.find((c) => c.value === record.comparator)
        return `${comparator?.label || record.comparator} ${record.threshold}`
      },
    },
    {
      title: 'Severity',
      dataIndex: 'severity',
      key: 'severity',
      render: (severity: string) => (
        <Tag color={getSeverityColor(severity)}>{severity.toUpperCase()}</Tag>
      ),
    },
    {
      title: 'Cooldown',
      dataIndex: 'cooldown_minutes',
      key: 'cooldown_minutes',
      render: (minutes: number) => `${minutes} min`,
    },
    {
      title: 'Recipients',
      key: 'recipients',
      render: (record: AlertPolicy) => (
        <Space>
          {record.recipients
            .filter((r) => r.enabled)
            .map((recipient) => (
              <Tag
                key={recipient.id}
                icon={recipient.type === 'email' ? <MailOutlined /> : <LinkOutlined />}
              >
                {recipient.type === 'email' ? (recipient as EmailRecipient).email : 'Webhook'}
              </Tag>
            ))}
        </Space>
      ),
    },
    {
      title: 'Status',
      dataIndex: 'enabled',
      key: 'enabled',
      render: (enabled: boolean, record: AlertPolicy) => (
        <Switch
          checked={enabled}
          onChange={(checked) => handleToggle(record.id, checked)}
          disabled={isReadonly}
          size="small"
        />
      ),
    },
    {
      title: 'Actions',
      key: 'actions',
      render: (record: AlertPolicy) => (
        <Space>
          <Button
            type="link"
            icon={<EditOutlined />}
            onClick={() => handleEdit(record)}
            disabled={isReadonly}
          >
            Edit
          </Button>
          <Popconfirm
            title="Are you sure you want to delete this policy?"
            onConfirm={() => handleDelete(record.id)}
            disabled={isReadonly}
          >
            <Button type="link" danger icon={<DeleteOutlined />} disabled={isReadonly}>
              Delete
            </Button>
          </Popconfirm>
        </Space>
      ),
    },
  ]

  const RecipientForm = () => (
    <Form.List name="recipients">
      {(fields, { add, remove }) => (
        <>
          {fields.map(({ key, name }) => (
            <Card key={key} size="small" style={{ marginBottom: 16 }}>
              <Row gutter={16}>
                <Col span={6}>
                  <Form.Item
                    name={[name, 'type']}
                    label="Type"
                    rules={[{ required: true, message: 'Select recipient type' }]}
                  >
                    <Select>
                      <Option value="email">Email</Option>
                      <Option value="webhook">Webhook</Option>
                    </Select>
                  </Form.Item>
                </Col>
                <Col span={12}>
                  <Form.Item
                    noStyle
                    shouldUpdate={(prevValues, currentValues) =>
                      prevValues.recipients?.[name]?.type !== currentValues.recipients?.[name]?.type
                    }
                  >
                    {({ getFieldValue }) => {
                      const recipientType = getFieldValue(['recipients', name, 'type'])
                      return (
                        <>
                          {recipientType === 'email' && (
                            <Form.Item
                              name={[name, 'email']}
                              label="Email"
                              rules={[
                                {
                                  required: true,
                                  message: 'Enter email address',
                                },
                                {
                                  type: 'email',
                                  message: 'Enter valid email',
                                },
                              ]}
                            >
                              <Input placeholder="Enter email address" />
                            </Form.Item>
                          )}
                          {recipientType === 'webhook' && (
                            <Form.Item
                              name={[name, 'url']}
                              label="Webhook URL"
                              rules={[
                                {
                                  required: true,
                                  message: 'Enter webhook URL',
                                },
                                {
                                  type: 'url',
                                  message: 'Enter valid URL',
                                },
                              ]}
                            >
                              <Input placeholder="Enter webhook URL" />
                            </Form.Item>
                          )}
                        </>
                      )
                    }}
                  </Form.Item>
                </Col>
                <Col span={4}>
                  <Form.Item
                    name={[name, 'enabled']}
                    label="Enabled"
                    valuePropName="checked"
                    initialValue={true}
                  >
                    <Switch />
                  </Form.Item>
                </Col>
                <Col span={2}>
                  <Button type="link" danger onClick={() => remove(name)} style={{ marginTop: 30 }}>
                    Remove
                  </Button>
                </Col>
              </Row>
            </Card>
          ))}
          <Button type="dashed" onClick={() => add()} icon={<PlusOutlined />}>
            Add Recipient
          </Button>
        </>
      )}
    </Form.List>
  )

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
        <Title level={2}>Alert Policies</Title>
        {!isReadonly && (
          <Button type="primary" icon={<PlusOutlined />} onClick={handleCreate}>
            Create Policy
          </Button>
        )}
      </div>

      <Table
        columns={columns}
        dataSource={policies}
        loading={loading}
        rowKey="id"
        pagination={{
          pageSize: 10,
          showSizeChanger: true,
          showTotal: (total) => `Total ${total} policies`,
        }}
      />

      <Drawer
        title={editingPolicy ? 'Edit Alert Policy' : 'Create Alert Policy'}
        width={720}
        open={drawerVisible}
        onClose={() => setDrawerVisible(false)}
        footer={
          <div style={{ textAlign: 'right' }}>
            <Button onClick={() => setDrawerVisible(false)} style={{ marginRight: 8 }}>
              Cancel
            </Button>
            <Button type="primary" onClick={() => form.submit()}>
              {editingPolicy ? 'Update' : 'Create'}
            </Button>
          </div>
        }
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={handleSubmit}
          initialValues={{
            comparator: 'greater_than',
            severity: 'medium',
            cooldown_minutes: 60,
          }}
        >
          <Form.Item
            name="name"
            label="Policy Name"
            rules={[
              { required: true, message: 'Enter policy name' },
              { max: 100, message: 'Name must be less than 100 characters' },
            ]}
          >
            <Input placeholder="Enter policy name" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Description"
            rules={[{ max: 500, message: 'Description must be less than 500 characters' }]}
          >
            <Input.TextArea rows={2} placeholder="Enter policy description" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="metric"
                label="Metric"
                rules={[{ required: true, message: 'Select a metric' }]}
              >
                <Select placeholder="Select metric">
                  {AVAILABLE_METRICS.map((metric) => (
                    <Option key={metric.value} value={metric.value}>
                      {metric.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="comparator"
                label="Comparator"
                rules={[{ required: true, message: 'Select comparator' }]}
              >
                <Select>
                  {COMPARATOR_OPTIONS.map((comp) => (
                    <Option key={comp.value} value={comp.value}>
                      {comp.label}
                    </Option>
                  ))}
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="threshold"
                label="Threshold"
                rules={[
                  { required: true, message: 'Enter threshold value' },
                  { type: 'number', min: 0, message: 'Threshold must be positive' },
                ]}
              >
                <InputNumber
                  style={{ width: '100%' }}
                  placeholder="Enter threshold"
                  min={0}
                  step={0.1}
                />
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="cooldown_minutes"
                label="Cooldown (minutes)"
                rules={[
                  { required: true, message: 'Enter cooldown period' },
                  { type: 'number', min: 1, message: 'Cooldown must be at least 1 minute' },
                ]}
              >
                <InputNumber style={{ width: '100%' }} placeholder="Enter cooldown" min={1} />
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="severity"
            label="Severity"
            rules={[{ required: true, message: 'Select severity level' }]}
          >
            <Select>
              {SEVERITY_OPTIONS.map((severity) => (
                <Option key={severity.value} value={severity.value}>
                  <Tag color={severity.color}>{severity.label}</Tag>
                </Option>
              ))}
            </Select>
          </Form.Item>

          <Form.Item label="Recipients">
            <RecipientForm />
          </Form.Item>
        </Form>
      </Drawer>
    </div>
  )
}

export default AlertPolicies
