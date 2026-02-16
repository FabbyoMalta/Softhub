import React from 'react'
import type { DayCapacity } from '../types'

const colorByRatio = (ratio: number) => {
  if (ratio >= 0.9) return 'bg-red-500'
  if (ratio >= 0.6) return 'bg-amber-500'
  return 'bg-emerald-500'
}

export function CapacityBar({ capacity }: { capacity: DayCapacity }) {
  const f1 = capacity.filial_1
  const f2 = capacity.filial_2
  const ratio1 = f1.limit > 0 ? Math.min(1, f1.count / f1.limit) : 0
  const ratio2 = f2.limit > 0 ? Math.min(1, f2.count / f2.limit) : 0
  const tooltip = `F1: ${f1.count}/${f1.limit} (${Math.max(0, f1.remaining)} vagas) | F2: ${f2.count}/${f2.limit} (${Math.max(0, f2.remaining)} vagas)`

  return (
    <div title={tooltip} className="space-y-1">
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full ${colorByRatio(ratio1)}`} style={{ width: `${Math.round(ratio1 * 100)}%` }} />
      </div>
      <div className="h-1.5 w-full overflow-hidden rounded-full bg-slate-200">
        <div className={`h-full ${colorByRatio(ratio2)}`} style={{ width: `${Math.round(ratio2 * 100)}%` }} />
      </div>
    </div>
  )
}
