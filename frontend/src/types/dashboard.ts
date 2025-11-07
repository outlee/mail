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
