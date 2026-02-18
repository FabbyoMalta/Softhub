import React, { useEffect, useMemo, useState } from 'react'
import { useToast } from '../components/Toast'
import type { BillingCase, BillingTicketBatchBody } from '../types'

const moneyFmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

const formatMoney = (raw: string | null) => {
  const value = Number(raw ?? '0')
  return Number.isFinite(value) ? moneyFmt.format(value) : '-'
}

async function parseApi<T>(res: Response): Promise<T> {
  const text = await res.text()
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} ${res.statusText}\n${text.slice(0, 500)}`)
  }
  return (text ? JSON.parse(text) : {}) as T
}

export function BillingPage({ apiBase }: { apiBase: string }) {
  const toast = useToast()
  const [cases, setCases] = useState<BillingCase[]>([])
  const [summary, setSummary] = useState<{ total_open: number; over_20: number; amount_open_sum: string } | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Record<string, boolean>>({})
  const [onlyOver20, setOnlyOver20] = useState(true)
  const [configWarning, setConfigWarning] = useState<string | null>(null)
  const [syncDueFrom, setSyncDueFrom] = useState(() => {
    const d = new Date()
    d.setDate(d.getDate() - 120)
    return d.toISOString().slice(0, 10)
  })

  const loadCases = async () => {
    setLoading(true)
    setError(null)
    const casesUrl = `${apiBase}/billing/cases?status=open&only_over_20_days=${onlyOver20 ? 'true' : 'false'}&limit=200&offset=0`
    const summaryUrl = `${apiBase}/billing/summary?status=open&only_over_20_days=${onlyOver20 ? 'true' : 'false'}`
    const cfgUrl = `${apiBase}/billing/ticket-config/check`
    console.info('[BillingPage] loading', { casesUrl, summaryUrl, cfgUrl })

    try {
      const [casesRes, summaryRes, cfgRes] = await Promise.all([fetch(casesUrl), fetch(summaryUrl), fetch(cfgUrl)])
      const casesPayload = await parseApi<BillingCase[]>(casesRes)
      const summaryPayload = await parseApi<{ total_open: number; over_20: number; amount_open_sum: string }>(summaryRes)
      const cfgPayload = await parseApi<{ ok: boolean; missing: string[]; enabled: boolean }>(cfgRes)
      setCases(casesPayload)
      setSummary(summaryPayload)
      if (!cfgPayload.enabled) {
        setConfigWarning('Tickets desabilitados (modo manual).')
      } else if (!cfgPayload.ok) {
        setConfigWarning(`Configurações ausentes: ${cfgPayload.missing.join(', ')}`)
      } else {
        setConfigWarning(null)
      }
    } catch (err: any) {
      setError(err?.message || 'Erro ao carregar billing')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCases()
  }, [apiBase, onlyOver20])

  const selectedIds = useMemo(() => Object.entries(selected).filter(([, v]) => v).map(([id]) => id), [selected])

  const runSync = async () => {
    const syncUrl = `${apiBase}/billing/sync?due_from=${encodeURIComponent(syncDueFrom)}&only_open=true&limit_pages=5&rp=500`
    console.info('[BillingPage] sync', { syncUrl })
    try {
      const res = await fetch(syncUrl, { method: 'POST' })
      const payload = await parseApi<{ synced: number; upserted: number; due_from_used: string }>(res)
      toast.success(`Sync concluído: synced=${payload.synced}, upserted=${payload.upserted}, due_from=${payload.due_from_used}`)
      await loadCases()
    } catch (err: any) {
      toast.error(err?.message || 'Erro no sync')
    }
  }

  const runBatchDry = async () => {
    const body: BillingTicketBatchBody = selectedIds.length ? { case_ids: selectedIds, limit: selectedIds.length } : { filters: { status: 'OPEN', min_days: 20 }, limit: 50 }
    try {
      const res = await fetch(`${apiBase}/billing/tickets/batch/dry-run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      })
      const payload = await parseApi<{ count: number; warnings: string[] }>(res)
      if (payload.warnings.length) toast.error(payload.warnings.join(' | '))
      else toast.success(`Dry-run OK: ${payload.count} elegíveis`)
    } catch (err: any) {
      toast.error(err?.message || 'Erro no dry-run')
    }
  }

  const runBatchCreate = async () => {
    if (!window.confirm('Confirma criação de tickets para os casos selecionados/filtro?')) return
    const body: BillingTicketBatchBody = selectedIds.length
      ? { case_ids: selectedIds, limit: selectedIds.length, require_confirm: true }
      : { filters: { status: 'OPEN', min_days: 20 }, limit: 50, require_confirm: true }

    try {
      const res = await fetch(`${apiBase}/billing/tickets/batch`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      })
      const payload = await parseApi<{ created: number; skipped: number; errors: number }>(res)
      toast.success(`Tickets criados: ${payload.created} (skip=${payload.skipped}, erros=${payload.errors})`)
      await loadCases()
    } catch (err: any) {
      toast.error(err?.message || 'Erro ao criar tickets')
    }
  }

  return (
    <section className="space-y-4">
      <header className="topbar rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-2xl font-bold text-slate-900">Billing 2.0</h2>
      </header>

      {configWarning ? <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-amber-700 text-sm">{configWarning}</div> : null}
      {error ? <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-rose-700 text-sm whitespace-pre-wrap">{error}</div> : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-sm text-slate-500">Cases OPEN</p><p className="text-2xl font-bold">{summary?.total_open ?? 0}</p></div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-sm text-slate-500">&gt;=20 dias</p><p className="text-2xl font-bold">{summary?.over_20 ?? 0}</p></div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-sm text-slate-500">Valor em aberto</p><p className="text-2xl font-bold">{formatMoney(summary?.amount_open_sum ?? '0')}</p></div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-2"><input type="checkbox" checked={onlyOver20} onChange={(e) => setOnlyOver20(e.target.checked)} />Somente 20+ dias</label>
        <label className="flex items-center gap-2">due_from sync: <input className="rounded border px-2 py-1" type="date" value={syncDueFrom} onChange={(e) => setSyncDueFrom(e.target.value)} /></label>
        <button className="btn" onClick={runSync}>Rodar Sync</button>
        <button className="btn" onClick={runBatchDry}>Dry-run (seleção)</button>
        <button className="btn primary" onClick={runBatchCreate}>Criar tickets (seleção)</button>
      </div>

      {loading ? <div className="rounded-2xl border border-slate-200 bg-white p-6 text-slate-500">Carregando billing...</div> : null}

      {!loading && cases.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 text-slate-600 text-sm">
          0 casos para os filtros atuais. Filtros usados: status=open, only_over_20_days={String(onlyOver20)}, due_from(sync)={syncDueFrom}.
        </div>
      ) : null}

      {!loading && cases.length > 0 ? (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-3 py-2"><input type="checkbox" onChange={(e) => setSelected(Object.fromEntries(cases.map((c) => [c.id, e.target.checked])))} /></th>
                <th className="px-3 py-2">Título</th>
                <th className="px-3 py-2">Cliente</th>
                <th className="px-3 py-2">Dias</th>
                <th className="px-3 py-2">Valor</th>
                <th className="px-3 py-2">Action state</th>
                <th className="px-3 py-2">Ticket status</th>
              </tr>
            </thead>
            <tbody>
              {cases.map((item) => (
                <tr key={item.id} className="border-t border-slate-100">
                  <td className="px-3 py-2"><input type="checkbox" checked={!!selected[item.id]} onChange={(e) => setSelected((prev) => ({ ...prev, [item.id]: e.target.checked }))} /></td>
                  <td className="px-3 py-2">{item.external_id}</td>
                  <td className="px-3 py-2">{(item.client_json?.nome as string) || item.id_cliente}</td>
                  <td className="px-3 py-2">{item.open_days}</td>
                  <td className="px-3 py-2">{formatMoney(item.amount_open)}</td>
                  <td className="px-3 py-2">{item.action_state}</td>
                  <td className="px-3 py-2">{item.ticket_status || '-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  )
}
