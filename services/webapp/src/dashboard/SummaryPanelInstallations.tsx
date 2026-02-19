import React from 'react'
import { DonutCompletion } from './DonutCompletion'
import { MetricCard } from './MetricCard'

type InstallationsData = {
  scheduledToday: number
  finishedToday: number
  pendingToday: number
  totalPeriod: number
  finishedPeriod: number
  pendingPeriod: number
}

export function SummaryPanelInstallations({ days, data }: { days: number; data: InstallationsData }) {
  const total = Math.max(1, data.totalPeriod)
  const finishedPct = Math.round((data.finishedPeriod / total) * 100)
  const pendingPct = Math.max(0, 100 - finishedPct)

  return (
    <section className="rounded-2xl border border-slate-200 border-t-4 border-t-blue-500 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Instalações</h3>
          <p className="text-sm text-slate-500">Resumo operacional do período</p>
        </div>
        <span className="rounded-full bg-blue-50 px-3 py-1 text-xs font-semibold text-blue-700">Período: {days} dias</span>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-4">
        <MetricCard title="Agendadas hoje" value={data.scheduledToday} live accent="blue" helper="Previstas (abertas + finalizadas)" />
        <MetricCard title="Finalizadas hoje" value={data.finishedToday} live accent="blue" helper="Atualização contínua" />
        <MetricCard title="Pendentes hoje" value={data.pendingToday} accent="amber" helper="Abertas com agendamento hoje" />
        <MetricCard title="Total período" value={data.totalPeriod} accent="blue" helper="Acumulado" />
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-[1fr_200px] md:items-center">
        <div>
          <DonutCompletion finished={data.finishedPeriod} pending={data.pendingPeriod} />
        </div>
        <div className="space-y-2">
          <div className="rounded-xl bg-blue-50 p-3">
            <p className="text-xs text-blue-700">Finalizadas</p>
            <p className="text-xl font-bold text-blue-900">{finishedPct}%</p>
          </div>
          <div className="rounded-xl bg-slate-100 p-3">
            <p className="text-xs text-slate-600">Pendentes</p>
            <p className="text-xl font-bold text-slate-900">{pendingPct}%</p>
          </div>
        </div>
      </div>
    </section>
  )
}
