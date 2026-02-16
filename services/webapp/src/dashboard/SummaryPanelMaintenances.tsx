import React from 'react'
import { MetricCard } from './MetricCard'
import { ProgressBar } from './ProgressBar'

type MaintData = {
  openedToday: number
  finishedToday: number
  openTotal: number
  totalPeriod: number
  resolvedPeriod: number
}

export function SummaryPanelMaintenances({ days, data, totalOSPeriod }: { days: number; data: MaintData; totalOSPeriod: number }) {
  const denominator = Math.max(1, data.totalPeriod)

  return (
    <section className="rounded-2xl border border-slate-200 border-t-4 border-t-amber-500 bg-white p-5 shadow-sm">
      <div className="mb-4 flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">Manutenções</h3>
          <p className="text-sm text-slate-500">Aberturas e resolução no período</p>
        </div>
        <span className="rounded-full bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-700">Período: {days} dias</span>
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-3">
        <MetricCard title="Abertas hoje" value={data.openedToday} live accent="amber" helper="Atualização contínua" />
        <MetricCard title="Finalizadas hoje" value={data.finishedToday} live accent="amber" helper="Atualização contínua" />
        <MetricCard title="Total período" value={data.totalPeriod} accent="amber" helper="Acumulado" />
      </div>

      <div className="mb-4 grid grid-cols-1 gap-3 md:grid-cols-2">
        <MetricCard title="Abertas total" value={data.openTotal} accent="amber" helper="Backlog atual" />
        <MetricCard title="Total OS período" value={totalOSPeriod} accent="slate" helper="Instalações + Manutenções" />
      </div>

      <ProgressBar label="Taxa de Resolução" value={data.resolvedPeriod} max={denominator} />
    </section>
  )
}
