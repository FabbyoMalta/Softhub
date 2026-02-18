import React, { useEffect, useMemo, useState } from 'react'
import { useToast } from '../components/Toast'
import type { BillingCase, BillingTicketBatchBody } from '../types'

const inputClass = 'rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100'

const moneyFmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

const formatMoney = (raw: string | null) => {
  const value = Number(raw ?? '0')
  return Number.isFinite(value) ? moneyFmt.format(value) : '-'
}

async function safeJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.text()
    throw new Error(body.slice(0, 400) || `Erro HTTP ${res.status}`)
  }
  return (await res.json()) as T
}

export function BillingPage({ apiBase }: { apiBase: string }) {
  const toast = useToast()
  const [cases, setCases] = useState<BillingCase[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [selected, setSelected] = useState<Record<string, boolean>>({})
  const [onlyOver20, setOnlyOver20] = useState(true)
  const [configWarning, setConfigWarning] = useState<string | null>(null)

  const loadCases = async () => {
    setLoading(true)
    setError(null)
    try {
      const query = new URLSearchParams({ status: 'OPEN', limit: '500', min_days: onlyOver20 ? '20' : '0' })
      const [casesRes, cfgRes] = await Promise.all([
        fetch(`${apiBase}/billing/cases?${query.toString()}`),
        fetch(`${apiBase}/billing/ticket-config/check`),
      ])
      const casesPayload = await safeJson<BillingCase[]>(casesRes)
      const cfgPayload = await safeJson<{ ok: boolean; missing: string[]; autoclose_enabled: boolean }>(cfgRes)
      setCases(casesPayload)
      setConfigWarning(cfgPayload.ok ? null : `Configurações ausentes: ${cfgPayload.missing.join(', ')}`)
    } catch (err: any) {
      setError(err?.message || 'Erro ao carregar billing cases')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadCases()
  }, [apiBase, onlyOver20])

  const selectedIds = useMemo(() => Object.entries(selected).filter(([, v]) => v).map(([id]) => id), [selected])

  const summary = useMemo(() => {
    const total = cases.length
    const totalAmount = cases.reduce((acc, item) => acc + Number(item.amount_open || '0'), 0)
    const over20 = cases.filter((item) => item.open_days >= 20).length
    return { total, totalAmount, over20 }
  }, [cases])

  const runBatchDry = async () => {
    const body: BillingTicketBatchBody = selectedIds.length ? { case_ids: selectedIds, limit: selectedIds.length } : { filters: { status: 'OPEN', min_days: 20 }, limit: 50 }
    try {
      const res = await fetch(`${apiBase}/billing/tickets/batch/dry-run`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
      })
      const payload = await safeJson<{ count: number; warnings: string[] }>(res)
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
      const payload = await safeJson<{ created: number; skipped: number; errors: number }>(res)
      toast.success(`Tickets criados: ${payload.created} (skip=${payload.skipped}, erros=${payload.errors})`)
      await loadCases()
    } catch (err: any) {
      toast.error(err?.message || 'Erro ao criar tickets')
    }
  }

  return (
    <section className="space-y-4">
      <header className="topbar rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Billing 2.0</h2>
          <p className="text-sm text-slate-500">Casos de cobrança em Postgres com ações manuais de ticket</p>
        </div>
      </header>

      {configWarning ? <div className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-amber-700 text-sm">{configWarning}</div> : null}

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-sm text-slate-500">Casos OPEN</p><p className="text-2xl font-bold">{summary.total}</p></div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-sm text-slate-500">&gt;= 20 dias</p><p className="text-2xl font-bold">{summary.over20}</p></div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-sm text-slate-500">Valor aberto</p><p className="text-2xl font-bold">{moneyFmt.format(summary.totalAmount)}</p></div>
      </div>

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm flex flex-wrap items-center gap-3">
        <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={onlyOver20} onChange={(e) => setOnlyOver20(e.target.checked)} />Somente 20+ dias</label>
        <button className="btn" onClick={runBatchDry}>Dry-run (seleção)</button>
        <button className="btn primary" onClick={runBatchCreate}>Criar tickets (seleção)</button>
      </div>

      {loading ? <div className="rounded-2xl border border-slate-200 bg-white p-6 text-slate-500">Carregando billing...</div> : null}
      {error ? <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700 text-sm">{error}</div> : null}

      {!loading ? (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-3 py-2"><input type="checkbox" onChange={(e) => setSelected(Object.fromEntries(cases.map((c) => [c.id, e.target.checked])))} /></th>
                <th className="px-3 py-2">Título</th>
                <th className="px-3 py-2">Cliente</th>
                <th className="px-3 py-2">Contrato</th>
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
                  <td className="px-3 py-2">{item.client_json?.nome as string || item.id_cliente}</td>
                  <td className="px-3 py-2">{item.id_contrato || '-'}</td>
                  <td className="px-3 py-2">{item.open_days}</td>
                  <td className="px-3 py-2">{formatMoney(item.amount_open)}</td>
                  <td className="px-3 py-2">{item.action_state}</td>
                  <td className="px-3 py-2">{item.ticket_status || '-'}</td>
                </tr>
              ))}
              {cases.length === 0 ? <tr><td colSpan={8} className="px-3 py-6 text-center text-slate-500">Sem itens</td></tr> : null}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  )
}
