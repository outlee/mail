import { Menu } from 'antd'
import { useNavigate, useLocation } from 'react-router-dom'
import { SettingOutlined, BellOutlined } from '@ant-design/icons'

interface AlertsNavigationProps {
  userRole: string
}

function AlertsNavigation({ userRole }: AlertsNavigationProps) {
  const navigate = useNavigate()
  const location = useLocation()

  const menuItems = [
    {
      key: '/alerts',
      icon: <BellOutlined />,
      label: 'Alerts',
    },
    {
      key: '/alert-policies',
      icon: <SettingOutlined />,
      label: 'Alert Policies',
      disabled: userRole === 'operator',
    },
  ]

  const handleMenuClick = ({ key }: { key: string }) => {
    navigate(key)
  }

  return (
    <Menu
      mode="horizontal"
      selectedKeys={[location.pathname]}
      items={menuItems}
      onClick={handleMenuClick}
      style={{ marginBottom: 24 }}
    />
  )
}

export default AlertsNavigation
