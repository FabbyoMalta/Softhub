import React, { useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { SummaryPanelInstallations } from './SummaryPanelInstallations'
import { SummaryPanelMaintenances } from './SummaryPanelMaintenances'
import { useDashboardSummary } from './useDashboardSummary'

const dateFormatter = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })
const toISODate = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
const parseISODate = (value: string) => {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, (month || 1) - 1, day || 1)
}

function DashboardSkeleton() {
  return (
    <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
      {Array.from({ length: 2 }).map((_, idx) => (
        <div key={idx} className="animate-pulse rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="mb-4 h-5 w-40 rounded bg-slate-200" />
          <div className="mb-3 grid grid-cols-3 gap-3">
            <div className="h-24 rounded-xl bg-slate-100" />
            <div className="h-24 rounded-xl bg-slate-100" />
            <div className="h-24 rounded-xl bg-slate-100" />
          </div>
          <div className="h-40 rounded-xl bg-slate-100" />
        </div>
      ))}
    </div>
  )
}

export function DashboardPage({ apiBase }: { apiBase: string }) {
  const navigate = useNavigate()
  const today = toISODate(new Date())
  const [startDate, setStartDate] = useState(today)
  const [days, setDays] = useState(7)
  const [period, setPeriod] = useState<'today' | '7d' | '14d' | '30d'>('7d')

  const { data, loading, error } = useDashboardSummary(apiBase, startDate, days, period)

  const periodLabel = useMemo(() => {
    if (!data?.periodStart || !data?.periodEnd) return '-'
    if (period === 'today') return 'Hoje'
    return `${dateFormatter.format(parseISODate(data.periodStart))} até ${dateFormatter.format(parseISODate(data.periodEnd))}`
  }, [data?.periodEnd, data?.periodStart])

  const onPeriodChange = (p: 'today' | '7d' | '14d' | '30d') => {
    setPeriod(p)
    if (p === 'today') {
      setStartDate(today)
      setDays(1)
    } else {
      setDays(Number(p.replace('d', '')))
    }
  }

  const onPeriodChange = (p: 'today' | '7d' | '14d' | '30d') => {
    setPeriod(p)
    if (p === 'today') {
      setStartDate(today)
      setDays(1)
    } else {
      setDays(Number(p.replace('d', '')))
    }
  }

  return (
    <section className="space-y-4">
      <header className="flex flex-col justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:flex-row md:items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Dashboard</h2>
          <p className="text-sm text-slate-500">Apenas indicadores sumarizados</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm text-slate-600">
            Período
            <select value={period} onChange={(e) => onPeriodChange(e.target.value as 'today' | '7d' | '14d' | '30d')} className="rounded-xl border border-slate-300 px-3 py-2">
              <option value="today">Hoje</option>
              <option value="7d">7 dias</option>
              <option value="14d">14 dias</option>
              <option value="30d">30 dias</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 text-sm text-slate-600">
            Início
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="rounded-xl border border-slate-300 px-3 py-2" />
          </label>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-medium text-slate-700">{periodLabel}</span>
        </div>
      </header>

      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700">
          <p className="font-medium">Não foi possível carregar os indicadores.</p>
          <p className="text-sm">{error}</p>
        </div>
      ) : null}

      {loading || !data ? (
        <DashboardSkeleton />
      ) : (
        <>
          <section className="rounded-2xl border border-amber-200 bg-amber-50/70 p-4 shadow-sm">
            <div className="mb-3 flex items-center justify-between">
              <h3 className="text-base font-semibold text-amber-900">Situação do Dia</h3>
              <span className="text-xs text-amber-800">{data.today.date}</span>
            </div>
            <div className="grid grid-cols-2 gap-2 md:grid-cols-4">
              <div className="rounded-xl bg-white p-2.5"><p className="text-xs text-slate-500">Previstas hoje</p><p className="text-2xl font-bold text-slate-900">{data.today.installs.scheduledTotal}</p></div>
              <div className="rounded-xl bg-white p-2.5"><p className="text-xs text-slate-500">Concluídas hoje</p><p className="text-2xl font-bold text-slate-900">{data.today.installs.completedToday}</p></div>
              <button
                type="button"
                aria-label="Ver OS atrasadas"
                title="Ver lista de OS atrasadas na Agenda"
                onClick={() => navigate('/agenda?view=overdue')}
                className="cursor-pointer rounded-xl border border-amber-300 bg-white p-2.5 text-left transition hover:bg-amber-50 hover:shadow-sm"
              >
                <p className="text-[11px] font-semibold uppercase tracking-wide text-amber-700">Crítico</p>
                <p className="text-xs text-slate-500">Atrasadas total</p>
                <p className="text-2xl font-bold text-amber-900">{data.today.installs.overdueTotal}</p>
                <p className="text-[11px] text-amber-700">Instalações abertas com agendamento antes de hoje</p>
              </button>
              <div className="rounded-xl bg-white p-2.5"><p className="text-xs text-slate-500">Cumprimento</p><p className="text-2xl font-bold text-slate-900">{Math.round((data.today.installs.completionRate || 0) * 100)}%</p></div>
            </div>
          </section>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <SummaryPanelInstallations days={days} data={data.installations} />
            <SummaryPanelMaintenances
              days={days}
              data={data.maintenances}
              totalOSPeriod={data.totals.osPeriod}
            />
            <button className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-left shadow-sm" onClick={() => navigate('/agenda?open_pending=true')}>
              <p className="text-sm font-semibold text-amber-800">OS pendentes</p>
              <p className="text-3xl font-bold text-amber-900">{data.installations.pendingInstallationsTotal}</p>
              <p className="text-xs text-amber-700">Instalações abertas com agendamento antes de hoje</p>
            </button>
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <div className="rounded-2xl border border-amber-300 bg-amber-50 p-4 shadow-sm">
              <p className="text-sm font-semibold text-amber-800">Pendentes hoje</p>
              <p className="text-3xl font-bold text-amber-900">{data.today.installs.pendingToday}</p>
              <p className="text-xs text-amber-700">Instalações abertas com data agendada para hoje</p>
            </div>
            <button className="rounded-2xl border border-amber-300 bg-amber-50 p-4 text-left shadow-sm" onClick={() => navigate('/agenda?open_pending=true')}>
              <p className="text-sm font-semibold text-amber-800">OS pendentes</p>
              <p className="text-3xl font-bold text-amber-900">{data.installations.pendingInstallationsTotal}</p>
              <p className="text-xs text-amber-700">Instalações abertas com agendamento antes de hoje</p>
            </button>
          </div>

        </>
      )}
    </section>
  )
}
