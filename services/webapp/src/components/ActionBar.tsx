import React from 'react'

export function ActionBar({ left, center, right }: { left?: React.ReactNode; center?: React.ReactNode; right?: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="grid gap-3 xl:grid-cols-[1.4fr_1fr_1.3fr] xl:items-end">
        <div>{left}</div>
        <div>{center}</div>
        <div className="xl:justify-self-end">{right}</div>
      </div>
    </div>
  )
}
