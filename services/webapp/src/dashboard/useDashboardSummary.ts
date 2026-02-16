import { useEffect, useMemo, useState } from 'react'

export type SummaryPoint = { date: string; count: number }

export type DashboardSummaryView = {
  periodStart: string
  periodEnd: string
  installations: {
    scheduledToday: number
    finishedToday: number
    totalPeriod: number
    finishedPeriod: number
    pendingPeriod: number
  }
  maintenances: {
    openedToday: number
    finishedToday: number
    openTotal: number
    totalPeriod: number
    resolvedPeriod: number
  }
  totals: { osPeriod: number }
  series?: {
    installationsScheduledByDay: SummaryPoint[]
    maintOpenedByDay: SummaryPoint[]
    maintClosedByDay: SummaryPoint[]
  }
}

type HookState = {
  data: DashboardSummaryView | null
  loading: boolean
  error: string | null
}

const CACHE_TTL_MS = 30_000
const cache = new Map<string, { expiresAt: number; data: DashboardSummaryView }>()

const safeNum = (value: unknown) => {
  const n = Number(value)
  return Number.isFinite(n) ? n : 0
}

const mapSummary = (raw: any): DashboardSummaryView => {
  const periodStart = String(raw?.period?.start ?? raw?.range?.start ?? '')
  const periodEnd = String(raw?.period?.end ?? raw?.range?.end ?? '')

  const installRaw = raw?.instalacoes ?? raw?.installations ?? {}
  const maintRaw = raw?.manutencoes ?? raw?.maintenances ?? {}

  const totalPeriodInstall = safeNum(installRaw?.total_periodo ?? installRaw?.total_period)
  const finishedTodayInstall = safeNum(installRaw?.finalizadas_hoje ?? installRaw?.finished_today)
  const finishedPeriodInstall = safeNum(installRaw?.finalizadas_periodo ?? installRaw?.finished_period)
  const pendingPeriodInstall = safeNum(installRaw?.pendentes_periodo ?? installRaw?.pending_period)

  const normalizedFinishedPeriod = finishedPeriodInstall > 0 ? finishedPeriodInstall : Math.max(0, totalPeriodInstall - pendingPeriodInstall)
  const normalizedPendingPeriod = pendingPeriodInstall > 0 ? pendingPeriodInstall : Math.max(0, totalPeriodInstall - normalizedFinishedPeriod)

  const openedTotalMaint = safeNum(maintRaw?.abertas_total ?? maintRaw?.open_total)
  const totalPeriodMaint = safeNum(maintRaw?.total_periodo ?? maintRaw?.total_period)
  const resolvedPeriodMaint = safeNum(maintRaw?.resolvidas_periodo ?? maintRaw?.resolved_period)

  return {
    periodStart,
    periodEnd,
    installations: {
      scheduledToday: safeNum(installRaw?.agendadas_hoje ?? installRaw?.scheduled_today),
      finishedToday: finishedTodayInstall,
      totalPeriod: totalPeriodInstall,
      finishedPeriod: normalizedFinishedPeriod,
      pendingPeriod: normalizedPendingPeriod,
    },
    maintenances: {
      openedToday: safeNum(maintRaw?.abertas_hoje ?? maintRaw?.opened_today),
      finishedToday: safeNum(maintRaw?.finalizadas_hoje ?? maintRaw?.finished_today),
      openTotal: openedTotalMaint,
      totalPeriod: totalPeriodMaint,
      resolvedPeriod: resolvedPeriodMaint,
    },
    totals: {
      osPeriod: safeNum(raw?.totals?.os_period) || totalPeriodInstall + totalPeriodMaint,
    },
    series: {
      installationsScheduledByDay: Array.isArray(raw?.installations_scheduled_by_day) ? raw.installations_scheduled_by_day : [],
      maintOpenedByDay: Array.isArray(raw?.maint_opened_by_day) ? raw.maint_opened_by_day : [],
      maintClosedByDay: Array.isArray(raw?.maint_closed_by_day) ? raw.maint_closed_by_day : [],
    },
  }
}

export function computeTrend(prev: number, curr: number): 'up' | 'down' | 'flat' {
  if (curr > prev) return 'up'
  if (curr < prev) return 'down'
  return 'flat'
}

export function useDashboardSummary(apiBase: string, startDate: string, days: number): HookState {
  const [state, setState] = useState<HookState>({ data: null, loading: true, error: null })

  const key = useMemo(() => `${startDate}:${days}`, [startDate, days])

  useEffect(() => {
    let isCancelled = false

    const controller = new AbortController()
    const timer = setTimeout(async () => {
      const cached = cache.get(key)
      if (cached && cached.expiresAt > Date.now()) {
        if (!isCancelled) setState({ data: cached.data, loading: false, error: null })
        return
      }

      if (!isCancelled) {
        setState((prev) => ({ ...prev, loading: true, error: null }))
      }

      try {
        const params = new URLSearchParams({ start: startDate, days: String(days) })
        const response = await fetch(`${apiBase}/dashboard/summary?${params.toString()}`, { signal: controller.signal })
        if (!response.ok) throw new Error('Não foi possível carregar os indicadores do dashboard.')
        const mapped = mapSummary(await response.json())
        cache.set(key, { data: mapped, expiresAt: Date.now() + CACHE_TTL_MS })
        if (!isCancelled) setState({ data: mapped, loading: false, error: null })
      } catch (err: any) {
        if (controller.signal.aborted || isCancelled) return
        setState({ data: null, loading: false, error: err?.message || 'Erro inesperado ao carregar o dashboard.' })
      }
    }, 300)

    return () => {
      isCancelled = true
      clearTimeout(timer)
      controller.abort()
    }
  }, [apiBase, days, key, startDate])

  return state
}
