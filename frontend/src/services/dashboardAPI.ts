import { apiClient } from './api'

export interface Asset {
  id: string
  name: string
  description?: string
  created_at: string
  updated_at: string
}

export interface KPISnapshot {
  id: string
  asset_id?: string
  group_id?: string
  kpi_type: string
  value: number
  period_start: string
  period_end: string
  created_at: string
}

export interface FailureEvent {
  id: string
  asset_id: string
  failure_mode: string
  failure_code?: string
  severity: string
  duration_minutes?: number
  start_time: string
  end_time?: string
  description?: string
  created_at: string
}

export interface AssetDetail extends Asset {
  latest_kpi?: KPISnapshot
  recent_failures: FailureEvent[]
}

export interface KPIStats {
  average_kpi: number
  min_kpi: number
  max_kpi: number
  total_assets: number
  total_failures: number
  failures_by_mode: { [key: string]: number }
}

export interface AssetSummary {
  id: string
  name: string
  avg_kpi: number
  failure_count: number
}

export const dashboardAPI = {
  getAssets: async (skip?: number, limit?: number): Promise<Asset[]> => {
    const response = await apiClient.get<Asset[]>('/assets', {
      params: { skip, limit },
    })
    return response.data
  },

  getAssetDetail: async (assetId: string): Promise<AssetDetail> => {
    const response = await apiClient.get<AssetDetail>(`/assets/${assetId}`)
    return response.data
  },

  getFailures: async (assetId?: string, skip?: number, limit?: number): Promise<FailureEvent[]> => {
    const response = await apiClient.get<FailureEvent[]>('/failures', {
      params: { asset_id: assetId, skip, limit },
    })
    return response.data
  },

  getFailure: async (failureId: string): Promise<FailureEvent> => {
    const response = await apiClient.get<FailureEvent>(`/failures/${failureId}`)
    return response.data
  },

  getDashboardStats: async (): Promise<KPIStats> => {
    const response = await apiClient.get<KPIStats>('/dashboard/stats')
    return response.data
  },

  getTopAssets: async (limit?: number): Promise<AssetSummary[]> => {
    const response = await apiClient.get<AssetSummary[]>('/dashboard/top-assets', {
      params: { limit },
    })
    return response.data
  },

  getBottomAssets: async (limit?: number): Promise<AssetSummary[]> => {
    const response = await apiClient.get<AssetSummary[]>('/dashboard/bottom-assets', {
      params: { limit },
    })
    return response.data
  },
}
