import axios, { AxiosError, AxiosRequestConfig, AxiosResponse } from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export interface TokenResponse {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RefreshTokenRequest {
  refresh_token: string
}

export interface UserInfo {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
}

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json',
  },
})

let isRefreshing = false
let refreshSubscribers: ((token: string) => void)[] = []

const subscribeTokenRefresh = (cb: (token: string) => void) => {
  refreshSubscribers.push(cb)
}

const onRefreshed = (token: string) => {
  refreshSubscribers.forEach((cb) => cb(token))
  refreshSubscribers = []
}

apiClient.interceptors.request.use(
  (config) => {
    const token = sessionStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

apiClient.interceptors.response.use(
  (response: AxiosResponse) => {
    return response
  },
  async (error: AxiosError) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean }

    if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
      if (isRefreshing) {
        return new Promise((resolve) => {
          subscribeTokenRefresh((token: string) => {
            if (originalRequest.headers) {
              originalRequest.headers.Authorization = `Bearer ${token}`
            }
            resolve(apiClient(originalRequest))
          })
        })
      }

      originalRequest._retry = true
      isRefreshing = true

      try {
        const refreshToken = sessionStorage.getItem('refresh_token')
        if (!refreshToken) {
          handleLogout()
          return Promise.reject(error)
        }

        const response = await axios.post<TokenResponse>(`${API_BASE_URL}/auth/refresh`, {
          refresh_token: refreshToken,
        })

        const { access_token, refresh_token } = response.data

        sessionStorage.setItem('access_token', access_token)
        sessionStorage.setItem('refresh_token', refresh_token)

        apiClient.defaults.headers.common.Authorization = `Bearer ${access_token}`
        if (originalRequest.headers) {
          originalRequest.headers.Authorization = `Bearer ${access_token}`
        }

        isRefreshing = false
        onRefreshed(access_token)

        return apiClient(originalRequest)
      } catch (refreshError) {
        handleLogout()
        isRefreshing = false
        return Promise.reject(refreshError)
      }
    }

    if (error.response?.status === 401) {
      handleLogout()
    }

    console.error('API Error:', error)
    return Promise.reject(error)
  }
)

const handleLogout = () => {
  sessionStorage.removeItem('access_token')
  sessionStorage.removeItem('refresh_token')
  window.location.href = '/login'
}

export const authAPI = {
  login: async (email: string, password: string): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/login', null, {
      params: { email, password },
    })
    return response.data
  },

  refresh: async (refreshToken: string): Promise<TokenResponse> => {
    const response = await apiClient.post<TokenResponse>('/auth/refresh', {
      refresh_token: refreshToken,
    })
    return response.data
  },

  logout: async (): Promise<void> => {
    await apiClient.post('/auth/logout')
    sessionStorage.removeItem('access_token')
    sessionStorage.removeItem('refresh_token')
  },

  me: async (): Promise<UserInfo> => {
    const response = await apiClient.get<UserInfo>('/auth/me')
    return response.data
  },
}
