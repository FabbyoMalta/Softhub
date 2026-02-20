import React, { useEffect, useMemo, useState } from 'react'
import { Copy, X } from 'lucide-react'
import type { DashboardItem } from '../types'

type OssMensagem = {
  id?: string
  data?: string
  mensagem?: string
  id_evento?: string | number
  id_tecnico?: string | number
  id_operador?: string | number
  status?: string
}

export function OsDrawer({ item, open, onClose, apiBase }: { item: DashboardItem | null; open: boolean; onClose: () => void; apiBase: string }) {
  const [messages, setMessages] = useState<OssMensagem[]>([])
  const [loadingMessages, setLoadingMessages] = useState(false)
  const [messagesError, setMessagesError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    const onKey = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  useEffect(() => {
    if (!open || !item?.id) return
    let cancelled = false

    const loadMessages = async () => {
      setLoadingMessages(true)
      setMessagesError(null)
      try {
        const url = `${apiBase}/oss/${item.id}/mensagens`
        const response = await fetch(url)
        const text = await response.text()
        if (!response.ok) throw new Error(`HTTP ${response.status} ${response.statusText}\n${text.slice(0, 300)}`)
        const payload = JSON.parse(text)
        if (!cancelled) setMessages(Array.isArray(payload?.registros) ? payload.registros : [])
      } catch (err: any) {
        if (!cancelled) {
          setMessages([])
          setMessagesError(err?.message || 'Falha ao carregar mensagens da OS')
        }
      } finally {
        if (!cancelled) setLoadingMessages(false)
      }
    }

    loadMessages()
    return () => {
      cancelled = true
    }
  }, [open, item?.id, apiBase])

  const sortedMessages = useMemo(() => [...messages].sort((a, b) => String(a.data || '').localeCompare(String(b.data || ''))), [messages])

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

        <div className="mt-6 border-t pt-4">
          <h4 className="mb-3 text-sm font-semibold text-slate-900">Timeline de mensagens</h4>
          {loadingMessages ? <p className="text-sm text-slate-500">Carregando mensagens...</p> : null}
          {messagesError ? <p className="whitespace-pre-wrap text-sm text-rose-600">{messagesError}</p> : null}
          {!loadingMessages && !messagesError && sortedMessages.length === 0 ? <p className="text-sm text-slate-500">Sem mensagens registradas</p> : null}

          <div className="space-y-3">
            {sortedMessages.map((msg, idx) => {
              const isMilestone = (msg.status || '').toUpperCase() === 'F'
              return (
                <div key={`${msg.id || idx}-${msg.data || ''}`} className="flex gap-3">
                  <div className={`mt-1 h-2.5 w-2.5 rounded-full ${isMilestone ? 'bg-emerald-600' : 'bg-slate-300'}`} />
                  <div className="min-w-0">
                    <p className="text-xs text-slate-500">{msg.data || '-'} {msg.id_evento ? `· evento ${msg.id_evento}` : ''}</p>
                    <p className="text-sm text-slate-800">{msg.mensagem || '-'}</p>
                    {(msg.id_tecnico || msg.id_operador) ? <p className="text-xs text-slate-500">tec: {msg.id_tecnico || '-'} · op: {msg.id_operador || '-'}</p> : null}
                  </div>
                </div>
              )
            })}
          </div>
        </div>
      </aside>
    </div>
  )
}
