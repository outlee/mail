import { useEffect, useState } from 'react'
import { Route, Routes, Navigate, useNavigate } from 'react-router-dom'
import { Layout, Button } from 'antd'
import { LogoutOutlined } from '@ant-design/icons'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import ProtectedRoute from './components/ProtectedRoute'
import AlertsLayout from './pages/AlertsLayout'
import AlertPolicies from './pages/AlertPolicies'
import Alerts from './pages/Alerts'
import Overview from './pages/Overview'
import AssetDetail from './pages/AssetDetail'
import FailureAnalysis from './pages/FailureAnalysis'
import { authAPI } from './services/api'
import './App.css'

const { Header, Content } = Layout

function App() {
  const [showHeader, setShowHeader] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    const token = sessionStorage.getItem('access_token')
    const path = window.location.pathname
    setShowHeader(!!token && path !== '/login')
  }, [])

  const handleLogout = async () => {
    try {
      await authAPI.logout()
    } catch (err) {
      console.error('Logout error:', err)
    } finally {
      sessionStorage.removeItem('access_token')
      sessionStorage.removeItem('refresh_token')
      setShowHeader(false)
      navigate('/login')
    }
  }

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {showHeader && (
        <Header
          style={{
            color: 'white',
            fontSize: '20px',
            fontWeight: 'bold',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span>MTBF Platform</span>
          <Button
            type="text"
            icon={<LogoutOutlined />}
            onClick={handleLogout}
            style={{ color: 'white' }}
          >
            Logout
          </Button>
        </Header>
      )}
      <Content style={{ padding: showHeader ? '24px' : '0' }}>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/dashboard"
            element={
              <ProtectedRoute>
                <Dashboard />
              </ProtectedRoute>
            }
          />
          <Route
            path="/overview"
            element={
              <ProtectedRoute>
                <Overview />
              </ProtectedRoute>
            }
          />
          <Route
            path="/assets/:id"
            element={
              <ProtectedRoute>
                <AssetDetail />
              </ProtectedRoute>
            }
          />
          <Route
            path="/failure-analysis"
            element={
              <ProtectedRoute>
                <FailureAnalysis />
              </ProtectedRoute>
            }
          />
          <Route
            path="/alerts/*"
            element={
              <ProtectedRoute>
                <AlertsLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<Alerts />} />
            <Route path="policies" element={<AlertPolicies />} />
          </Route>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </Content>
    </Layout>
  )
}

export default App
