import React, { useMemo, useState } from 'react'
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { SummaryPanelInstallations } from './SummaryPanelInstallations'
import { SummaryPanelMaintenances } from './SummaryPanelMaintenances'
import { computeTrend, useDashboardSummary } from './useDashboardSummary'

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

function TinySeriesPreview({ title, data }: { title: string; data: Array<{ date: string; count: number }> }) {
  if (!data.length) return null

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="mb-2 text-sm font-medium text-slate-700">{title}</p>
      <div className="h-24 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={data}>
            <XAxis dataKey="date" hide />
            <YAxis hide />
            <Tooltip />
            <Line type="monotone" dataKey="count" stroke="#0ea5e9" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  )
}

export function DashboardPage({ apiBase }: { apiBase: string }) {
  const [startDate, setStartDate] = useState(toISODate(new Date()))
  const [days, setDays] = useState(7)

  const { data, loading, error } = useDashboardSummary(apiBase, startDate, days)

  const periodLabel = useMemo(() => {
    if (!data?.periodStart || !data?.periodEnd) return '-'
    return `${dateFormatter.format(parseISODate(data.periodStart))} até ${dateFormatter.format(parseISODate(data.periodEnd))}`
  }, [data?.periodEnd, data?.periodStart])

  const trendPlaceholder = computeTrend(0, data?.totals.osPeriod ?? 0)
  const maintResolvedPeriod = Math.max(0, (data?.maintenances.totalPeriod ?? 0) - (data?.maintenances.openTotal ?? 0))

  return (
    <section className="space-y-4">
      <header className="flex flex-col justify-between gap-3 rounded-2xl border border-slate-200 bg-white p-5 shadow-sm md:flex-row md:items-center">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Dashboard</h2>
          <p className="text-sm text-slate-500">Apenas indicadores sumarizados</p>
        </div>
        <div className="flex flex-wrap items-end gap-3">
          <label className="flex flex-col gap-1 text-sm text-slate-600">
            Início
            <input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} className="rounded-xl border border-slate-300 px-3 py-2" />
          </label>
          <label className="flex flex-col gap-1 text-sm text-slate-600">
            Dias
            <select value={days} onChange={(e) => setDays(Number(e.target.value))} className="rounded-xl border border-slate-300 px-3 py-2">
              <option value={7}>7</option>
              <option value={14}>14</option>
              <option value={30}>30</option>
            </select>
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
          <div className="grid grid-cols-1 gap-4 xl:grid-cols-2">
            <SummaryPanelInstallations days={days} data={data.installations} />
            <SummaryPanelMaintenances
              days={days}
              data={data.maintenances}
              totalOSPeriod={data.totals.osPeriod}
            />
          </div>

          <div className="grid grid-cols-1 gap-4 xl:grid-cols-3">
            <TinySeriesPreview title="Instalações agendadas por dia" data={data.series?.installationsScheduledByDay || []} />
            <TinySeriesPreview title="Manutenções abertas por dia" data={data.series?.maintOpenedByDay || []} />
            <TinySeriesPreview title="Manutenções finalizadas por dia" data={data.series?.maintClosedByDay || []} />
          </div>

          <p className="text-xs text-slate-400">Tendência (placeholder): {trendPlaceholder}</p>
          <p className="hidden">Taxa de resolução (base período): {maintResolvedPeriod}</p>
        </>
      )}
    </section>
  )
}
