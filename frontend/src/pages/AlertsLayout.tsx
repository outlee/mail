import { useEffect, useState } from 'react'
import { Outlet } from 'react-router-dom'
import { authAPI } from '../services/api'
import AlertsNavigation from '../components/AlertsNavigation'
import type { UserInfo } from '../services/api'

function AlertsLayout() {
  const [user, setUser] = useState<UserInfo | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const loadUser = async () => {
      try {
        const userData = await authAPI.me()
        setUser(userData)
      } catch (error) {
        console.error('Failed to load user info:', error)
      } finally {
        setLoading(false)
      }
    }

    loadUser()
  }, [])

  if (loading) {
    return <div>Loading...</div>
  }

  if (!user) {
    return <div>Error: Unable to load user information</div>
  }

  return (
    <div>
      <AlertsNavigation userRole={user.role} />
      <Outlet />
    </div>
  )
}

export default AlertsLayout
