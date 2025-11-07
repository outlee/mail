import { ReactNode, useEffect, useState } from 'react'
import { Navigate } from 'react-router-dom'
import { Spin } from 'antd'
import { authAPI } from '../services/api'

interface ProtectedRouteProps {
  children: ReactNode
  requiredRoles?: string[]
}

function ProtectedRoute({ children, requiredRoles }: ProtectedRouteProps) {
  const [isLoading, setIsLoading] = useState(true)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [userRole, setUserRole] = useState<string | null>(null)

  useEffect(() => {
    const checkAuth = async () => {
      const token = sessionStorage.getItem('access_token')

      if (!token) {
        setIsAuthenticated(false)
        setIsLoading(false)
        return
      }

      try {
        const user = await authAPI.me()
        setUserRole(user.role)

        if (requiredRoles && !requiredRoles.includes(user.role)) {
          setIsAuthenticated(false)
        } else {
          setIsAuthenticated(true)
        }
      } catch (err) {
        console.error('Failed to verify authentication:', err)
        setIsAuthenticated(false)
        sessionStorage.removeItem('access_token')
        sessionStorage.removeItem('refresh_token')
      } finally {
        setIsLoading(false)
      }
    }

    checkAuth()
  }, [requiredRoles])

  if (isLoading) {
    return (
      <div style={{ display: 'flex', justifyContent: 'center', padding: '50px' }}>
        <Spin size="large" />
      </div>
    )
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  if (requiredRoles && userRole && !requiredRoles.includes(userRole)) {
    return <Navigate to="/dashboard" replace />
  }

  return <>{children}</>
}

export default ProtectedRoute
