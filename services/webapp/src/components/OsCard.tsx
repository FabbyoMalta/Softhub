import React from 'react'
import { Clock3, MapPin, Wrench } from 'lucide-react'
import type { DashboardItem } from '../types'

const statusClass = (code: string) => {
  if (code === 'AG') return 'bg-blue-100 text-blue-700'
  if (code === 'EX' || code === 'DS') return 'bg-amber-100 text-amber-700'
  if (code === 'F') return 'bg-emerald-100 text-emerald-700'
  if (code === 'RAG') return 'bg-slate-200 text-slate-700'
  return 'bg-slate-100 text-slate-700'
}

const typeClass = (type: DashboardItem['type']) => {
  if (type === 'instalacao') return 'bg-sky-100 text-sky-700'
  if (type === 'manutencao') return 'bg-orange-100 text-orange-700'
  return 'bg-slate-100 text-slate-700'
}

export function OsCard({ item, onClick }: { item: DashboardItem; onClick: () => void }) {
  const isDone = (item.status_code || '') === 'F'
  return (
    <button
      type="button"
      onClick={onClick}
      className={`w-full rounded-xl border p-3 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md ${
        isDone ? 'border-emerald-200 bg-emerald-50/50 opacity-90' : 'border-slate-200 bg-white'
      }`}
    >
      <div className="mb-2 flex items-center justify-between gap-2">
        <div className="inline-flex items-center gap-1 text-sm font-semibold text-slate-700"><Clock3 size={14} />{item.time || '--:--'}</div>
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${statusClass(item.status_code || '')}`}>{isDone ? 'Finalizada' : (item.status_code || '-')}</span>
      </div>
      <p className="line-clamp-1 text-sm font-semibold text-slate-900">{item.customer_name || 'Cliente não informado'}</p>
      <p className="mt-1 inline-flex items-center gap-1 text-xs text-slate-600"><MapPin size={13} />{item.bairro || '-'} · {item.cidade || '-'}</p>
      <div className={`mt-2 inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium ${typeClass(item.type)}`}>
        <Wrench size={12} />
        <span>{item.type}</span>
      </div>
    </button>
  )
}
