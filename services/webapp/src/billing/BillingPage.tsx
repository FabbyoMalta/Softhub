import React, { useEffect, useState } from 'react'
import { useToast } from '../components/Toast'

const moneyFmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

type BillingTitle = {
  external_id: string
  due_date: string | null
  issue_date: string | null
  amount_open: string
  amount_total: string | null
  payment_type: string | null
  open_days: number
  status: string | null
  id_cobranca: string | null
  linha_digitavel: string | null
}

type BillingCaseGroup = {
  case_key: string
  id_cliente: string
  id_contrato: string | null
  cliente_nome: string | null
  qtd_titulos: number
  total_aberto: string
  oldest_due_date: string | null
  newest_due_date: string | null
  max_open_days: number
  titles: BillingTitle[]
}

type BillingCasesPayload = {
  summary: {
    cases_total: number
    cases_20p: number
    titles_total: number
    amount_open_total: string
    oldest_due_date: string | null
    generated_at: string
  }
  cases: BillingCaseGroup[]
}

async function parseApi<T>(res: Response): Promise<T> {
  const text = await res.text()
  if (!res.ok) {
    throw new Error(`HTTP ${res.status} ${res.statusText}\n${text.slice(0, 500)}`)
  }
  return (text ? JSON.parse(text) : {}) as T
}

const formatMoney = (raw: string | null) => {
  const value = Number(raw ?? '0')
  return Number.isFinite(value) ? moneyFmt.format(value) : '-'
}

export function BillingPage({ apiBase }: { apiBase: string }) {
  const toast = useToast()
  const [payload, setPayload] = useState<BillingCasesPayload | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [only20p, setOnly20p] = useState(true)
  const [groupBy, setGroupBy] = useState<'contract' | 'client'>('contract')
  const [minDueDate, setMinDueDate] = useState('')
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const query = new URLSearchParams({
        only_20p: String(only20p),
        group_by: groupBy,
        limit: '500',
      })
      if (minDueDate) query.set('min_due_date', minDueDate)
      const url = `${apiBase}/billing/cases?${query.toString()}`
      console.info('[BillingPage] fetch billing cases', { url })
      const res = await fetch(url)
      const data = await parseApi<BillingCasesPayload>(res)
      setPayload(data)
      toast.success(`Carregado: ${data.summary.cases_total} casos`)
    } catch (err: any) {
      setError(err?.message || 'Erro ao carregar billing cases')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const rows = payload?.cases || []
  const summary = payload?.summary

  return (
    <section className="space-y-4">
      <header className="topbar rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="text-2xl font-bold text-slate-900">Billing 2.0</h2>
      </header>

      {error ? <div className="rounded-xl border border-rose-200 bg-rose-50 p-3 text-rose-700 text-sm whitespace-pre-wrap">{error}</div> : null}

      <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm flex flex-wrap items-center gap-3 text-sm">
        <label className="flex items-center gap-2"><input type="checkbox" checked={only20p} onChange={(e) => setOnly20p(e.target.checked)} />Somente 20+ dias</label>
        <label className="flex items-center gap-2">Agrupar por:
          <select className="rounded border px-2 py-1" value={groupBy} onChange={(e) => setGroupBy(e.target.value as 'contract' | 'client')}>
            <option value="contract">Contrato (padrão)</option>
            <option value="client">Cliente</option>
          </select>
        </label>
        <label className="flex items-center gap-2">Vencimento a partir de:
          <input className="rounded border px-2 py-1" type="date" value={minDueDate} onChange={(e) => setMinDueDate(e.target.value)} />
        </label>
        <button className="btn" onClick={load}>Recarregar</button>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-xs text-slate-500">Casos totais</p><p className="text-2xl font-bold">{summary?.cases_total ?? 0}</p></div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-xs text-slate-500">Casos 20+</p><p className="text-2xl font-bold">{summary?.cases_20p ?? 0}</p></div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-xs text-slate-500">Valor aberto</p><p className="text-2xl font-bold">{formatMoney(summary?.amount_open_total ?? '0')}</p></div>
        <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"><p className="text-xs text-slate-500">Vencimento mais antigo</p><p className="text-2xl font-bold">{summary?.oldest_due_date ?? '-'}</p></div>
      </div>

      {loading ? <div className="rounded-2xl border border-slate-200 bg-white p-6 text-slate-500">Carregando...</div> : null}

      {!loading && rows.length === 0 ? (
        <div className="rounded-2xl border border-slate-200 bg-white p-4 text-slate-600 text-sm">Sem casos para o filtro atual.</div>
      ) : null}

      {!loading && rows.length > 0 ? (
        <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-600">
              <tr>
                <th className="px-3 py-2"></th>
                <th className="px-3 py-2">Cliente</th>
                <th className="px-3 py-2">Contrato</th>
                <th className="px-3 py-2">Qtd títulos</th>
                <th className="px-3 py-2">Total aberto</th>
                <th className="px-3 py-2">Faixa vencimento</th>
                <th className="px-3 py-2">Maior atraso</th>
                <th className="px-3 py-2">Ticket status</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((item) => (
                <React.Fragment key={item.case_key}>
                  <tr className="border-t border-slate-100">
                    <td className="px-3 py-2"><button className="btn" onClick={() => setExpanded((prev) => ({ ...prev, [item.case_key]: !prev[item.case_key] }))}>{expanded[item.case_key] ? '▾' : '▸'}</button></td>
                    <td className="px-3 py-2">{item.cliente_nome || item.id_cliente}</td>
                    <td className="px-3 py-2">{item.id_contrato || '-'}</td>
                    <td className="px-3 py-2">{item.qtd_titulos}</td>
                    <td className="px-3 py-2">{formatMoney(item.total_aberto)}</td>
                    <td className="px-3 py-2">{item.oldest_due_date || '-'} → {item.newest_due_date || '-'}</td>
                    <td className="px-3 py-2">{item.max_open_days}</td>
                    <td className="px-3 py-2">-</td>
                  </tr>
                  {expanded[item.case_key] ? (
                    <tr>
                      <td colSpan={8} className="px-3 py-2 bg-slate-50">
                        <table className="min-w-full text-xs">
                          <thead>
                            <tr className="text-slate-500">
                              <th className="px-2 py-1 text-left">ID título</th>
                              <th className="px-2 py-1 text-left">Emissão</th>
                              <th className="px-2 py-1 text-left">Vencimento</th>
                              <th className="px-2 py-1 text-left">Valor aberto</th>
                              <th className="px-2 py-1 text-left">Dias em aberto</th>
                              <th className="px-2 py-1 text-left">Tipo</th>
                            </tr>
                          </thead>
                          <tbody>
                            {item.titles.map((t) => (
                              <tr key={t.external_id} className="border-t border-slate-200">
                                <td className="px-2 py-1">{t.external_id}</td>
                                <td className="px-2 py-1">{t.issue_date || '-'}</td>
                                <td className="px-2 py-1">{t.due_date || '-'}</td>
                                <td className="px-2 py-1">{formatMoney(t.amount_open)}</td>
                                <td className="px-2 py-1">{t.open_days}</td>
                                <td className="px-2 py-1">{t.payment_type || '-'}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </td>
                    </tr>
                  ) : null}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      ) : null}
    </section>
  )
}
