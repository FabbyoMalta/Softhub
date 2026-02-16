import React from 'react'

type MetricCardProps = {
  title: string
  value: number
  live?: boolean
  accent?: 'blue' | 'amber' | 'slate'
  helper?: string
}

const accentClass: Record<NonNullable<MetricCardProps['accent']>, string> = {
  blue: 'text-blue-700 bg-blue-50',
  amber: 'text-amber-700 bg-amber-50',
  slate: 'text-slate-700 bg-slate-100',
}

export function MetricCard({ title, value, live, accent = 'slate', helper }: MetricCardProps) {
  return (
    <article className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2 flex items-center justify-between">
        <p className="text-sm text-slate-600">{title}</p>
        {live ? <span className="h-2.5 w-2.5 animate-pulse rounded-full bg-emerald-500" aria-label="ao vivo" /> : null}
      </div>
      <p className="text-3xl font-bold text-slate-900">{value}</p>
      {helper ? <span className={`mt-2 inline-flex rounded-full px-2.5 py-1 text-xs font-medium ${accentClass[accent]}`}>{helper}</span> : null}
    </article>
  )
}
