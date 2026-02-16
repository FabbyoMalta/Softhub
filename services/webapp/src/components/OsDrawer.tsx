import React, { useEffect } from 'react'
import { Copy, X } from 'lucide-react'
import type { DashboardItem } from '../types'

export function OsDrawer({ item, open, onClose }: { item: DashboardItem | null; open: boolean; onClose: () => void }) {
  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  if (!open || !item) return null

  const copy = async (value: string) => {
    if (!value) return
    try {
      await navigator.clipboard.writeText(value)
    } catch {
      // noop
    }
  }

  return (
    <div className="fixed inset-0 z-50">
      <button className="absolute inset-0 bg-black/30" onClick={onClose} aria-label="Fechar drawer" />
      <aside className="absolute right-0 top-0 h-full w-full max-w-md overflow-y-auto bg-white p-5 shadow-2xl">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-lg font-semibold">OS {item.id}</h3>
          <button className="rounded-lg border p-2" onClick={onClose}><X size={16} /></button>
        </div>
        <div className="space-y-2 text-sm text-slate-700">
          <p><strong>Cliente:</strong> {item.customer_name || '-'}</p>
          <p><strong>Status:</strong> {item.status_label || item.status_code || '-'}</p>
          <p><strong>Assunto:</strong> {item.type}</p>
          <p><strong>Filial:</strong> {item.id_filial || '-'}</p>
          <p><strong>Data agenda:</strong> {item.scheduled_at || '-'}</p>
          <p><strong>Bairro/Cidade:</strong> {item.bairro || '-'} / {item.cidade || '-'}</p>
          <p><strong>ID cliente:</strong> {item.id_cliente || '-'}</p>
          <p><strong>Protocolo:</strong> {item.protocolo || '-'}</p>
        </div>
        <div className="mt-5 flex gap-2">
          <button className="inline-flex items-center gap-1 rounded-lg border px-3 py-2 text-sm" onClick={() => copy(item.protocolo || '')}><Copy size={14} />Copiar protocolo</button>
          <button className="inline-flex items-center gap-1 rounded-lg border px-3 py-2 text-sm" onClick={() => copy(`${item.bairro || ''} ${item.cidade || ''}`)}><Copy size={14} />Copiar endereço</button>
        </div>
      </aside>
    </div>
  )
}
