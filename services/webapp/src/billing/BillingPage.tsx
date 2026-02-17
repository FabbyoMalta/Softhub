import React, { useEffect, useMemo, useState } from 'react'
import type { BillingAction, BillingOpenItem, BillingOpenResponse } from '../types'

const inputClass = 'rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100'

type BillingFilters = {
  onlyOver20: boolean
  paymentType: string
  seller: string
  contractStatus: string
  search: string
}

function SummaryCard({ title, value, helper }: { title: string; value: string | number; helper?: string }) {
  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
      <p className="text-sm text-slate-500">{title}</p>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      {helper ? <p className="text-xs text-slate-400">{helper}</p> : null}
    </div>
  )
}

const moneyFmt = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'BRL' })

const formatMoney = (raw: string | null) => {
  const value = Number(raw ?? '0')
  return Number.isFinite(value) ? moneyFmt.format(value) : '-'
}

export function BillingPage({ apiBase }: { apiBase: string }) {
  const [data, setData] = useState<BillingOpenResponse | null>(null)
  const [actions, setActions] = useState<BillingAction[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [filters, setFilters] = useState<BillingFilters>({
    onlyOver20: false,
    paymentType: '',
    seller: '',
    contractStatus: '',
    search: '',
  })

  useEffect(() => {
    let cancelled = false
    const run = async () => {
      setLoading(true)
      setError(null)
      const openUrl = `${apiBase}/billing/open`
      const actionsUrl = `${apiBase}/billing/actions?limit=100`
      console.info('[BillingPage] loading data', { openUrl, actionsUrl })
      try {
        const [openRes, actionsRes] = await Promise.all([
          fetch(openUrl),
          fetch(actionsUrl),
        ])
        if (!openRes.ok) {
          const body = await openRes.text()
          throw new Error(`Falha ao carregar contas em aberto (${openRes.status} ${openRes.statusText})\n${body.slice(0, 300)}`)
        }

        const openJson = (await openRes.json()) as BillingOpenResponse
        let actionsJson: BillingAction[] = []
        if (actionsRes.ok) {
          actionsJson = (await actionsRes.json()) as BillingAction[]
        } else {
          const body = await actionsRes.text()
          throw new Error(`Falha ao carregar ações de billing (${actionsRes.status} ${actionsRes.statusText})\n${body.slice(0, 300)}`)
        }

        if (!cancelled) {
          setData(openJson)
          setActions(actionsJson)
        }
      } catch (err: any) {
        if (!cancelled) setError(err?.message || 'Erro inesperado ao carregar billing')
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    run()
    return () => {
      cancelled = true
    }
  }, [apiBase])

  const paymentTypes = useMemo(
    () => Array.from(new Set((data?.items || []).map((item) => item.payment_type || '').filter(Boolean))).sort(),
    [data?.items],
  )
  const sellers = useMemo(
    () => Array.from(new Set((data?.items || []).map((item) => item.contract?.id_vendedor || '').filter(Boolean))).sort(),
    [data?.items],
  )
  const contractStatuses = useMemo(
    () => Array.from(new Set((data?.items || []).map((item) => item.contract?.status || '').filter(Boolean))).sort(),
    [data?.items],
  )

  const filtered = useMemo(() => {
    const term = filters.search.trim().toLowerCase()
    return (data?.items || []).filter((item: BillingOpenItem) => {
      if (filters.onlyOver20 && item.open_days < 20) return false
      if (filters.paymentType && (item.payment_type || '') !== filters.paymentType) return false
      if (filters.seller && (item.contract?.id_vendedor || '') !== filters.seller) return false
      if (filters.contractStatus && (item.contract?.status || '') !== filters.contractStatus) return false
      if (!term) return true
      const hay = `${item.id_cliente || ''} ${item.id_contrato || ''}`.toLowerCase()
      return hay.includes(term)
    })
  }, [data?.items, filters])

  return (
    <section className="space-y-4">
      <header className="topbar rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div>
          <h2 className="text-2xl font-bold text-slate-900">Billing</h2>
          <p className="text-sm text-slate-500">Contas a receber abertas + marcação automática de 20 dias</p>
        </div>
      </header>

      {loading ? <div className="rounded-2xl border border-slate-200 bg-white p-6 text-slate-500">Carregando billing...</div> : null}
      {error ? (
        <div className="rounded-2xl border border-rose-200 bg-rose-50 p-4 text-rose-700">
          <p className="font-semibold">Erro ao carregar billing</p>
          <pre className="mt-2 whitespace-pre-wrap text-xs">{error}</pre>
        </div>
      ) : null}

      {!loading && data ? (
        <>
          <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <SummaryCard title="Total em aberto" value={data.summary.total_open} />
            <SummaryCard title=">= 20 dias" value={data.summary.over_20_days} helper="Critério de ação" />
            <SummaryCard title="Vencimento mais antigo" value={data.summary.oldest_due_date || '-'} />
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <div className="grid grid-cols-1 gap-3 md:grid-cols-5">
              <label className="flex items-center gap-2 text-sm text-slate-700">
                <input type="checkbox" checked={filters.onlyOver20} onChange={(e) => setFilters((f) => ({ ...f, onlyOver20: e.target.checked }))} />
                Somente 20+ dias
              </label>
              <select className={inputClass} value={filters.paymentType} onChange={(e) => setFilters((f) => ({ ...f, paymentType: e.target.value }))}>
                <option value="">Tipo de recebimento</option>
                {paymentTypes.map((type) => <option key={type} value={type}>{type}</option>)}
              </select>
              <select className={inputClass} value={filters.seller} onChange={(e) => setFilters((f) => ({ ...f, seller: e.target.value }))}>
                <option value="">Vendedor</option>
                {sellers.map((seller) => <option key={seller} value={seller}>{seller}</option>)}
              </select>
              <select className={inputClass} value={filters.contractStatus} onChange={(e) => setFilters((f) => ({ ...f, contractStatus: e.target.value }))}>
                <option value="">Status contrato</option>
                {contractStatuses.map((status) => <option key={status} value={status}>{status}</option>)}
              </select>
              <input className={inputClass} placeholder="Buscar cliente/contrato" value={filters.search} onChange={(e) => setFilters((f) => ({ ...f, search: e.target.value }))} />
            </div>
          </div>

          <div className="overflow-x-auto rounded-2xl border border-slate-200 bg-white shadow-sm">
            <table className="min-w-full text-sm">
              <thead className="bg-slate-50 text-left text-slate-600">
                <tr>
                  <th className="px-3 py-2">External ID</th>
                  <th className="px-3 py-2">Cliente</th>
                  <th className="px-3 py-2">Contrato</th>
                  <th className="px-3 py-2">Venc.</th>
                  <th className="px-3 py-2">Dias</th>
                  <th className="px-3 py-2">Aberto/Total</th>
                  <th className="px-3 py-2">Pagamento</th>
                  <th className="px-3 py-2">Contrato (status)</th>
                </tr>
              </thead>
              <tbody>
                {filtered.map((item) => (
                  <tr key={`${item.external_id}-${item.id_contrato}`} className="border-t border-slate-100">
                    <td className="px-3 py-2">{item.external_id || '-'}</td>
                    <td className="px-3 py-2">{item.id_cliente || '-'}</td>
                    <td className="px-3 py-2">{item.id_contrato || '-'}</td>
                    <td className="px-3 py-2">{item.due_date || '-'}</td>
                    <td className="px-3 py-2">
                      <span className={`rounded-full px-2 py-1 text-xs font-semibold ${item.open_days >= 20 ? 'bg-rose-100 text-rose-700' : 'bg-slate-100 text-slate-700'}`}>
                        {item.open_days}
                      </span>
                    </td>
                    <td className="px-3 py-2">{formatMoney(item.amount_open)} / {formatMoney(item.amount_total)}</td>
                    <td className="px-3 py-2">{item.payment_type || '-'}</td>
                    <td className="px-3 py-2">
                      <div className="flex flex-col text-xs">
                        <span>{item.contract?.status || '-'}</span>
                        <span className="text-slate-500">Internet: {item.contract?.status_internet || '-'}</span>
                        <span className="text-slate-500">Financeiro: {item.contract?.situacao_financeira || '-'}</span>
                        <span className="text-slate-500">Vendedor: {item.contract?.id_vendedor || '-'}</span>
                        <span className="text-slate-500">Plano: {item.contract?.plano_nome || '-'}</span>
                      </div>
                    </td>
                  </tr>
                ))}
                {filtered.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="px-3 py-6 text-center text-slate-500">Sem itens</td>
                  </tr>
                ) : null}
              </tbody>
            </table>
          </div>

          <div className="rounded-2xl border border-slate-200 bg-white p-4 shadow-sm">
            <h3 className="mb-2 text-sm font-semibold text-slate-800">Ações disparadas</h3>
            {actions.length === 0 ? (
              <p className="text-sm text-slate-500">Nenhuma ação registrada.</p>
            ) : (
              <ul className="list-disc space-y-1 pl-5 text-sm text-slate-700">
                {actions.slice(0, 10).map((action) => (
                  <li key={action.action_key}>{action.action_key} · external_id {action.external_id}</li>
                ))}
              </ul>
            )}
          </div>
        </>
      ) : null}
    </section>
  )
}
