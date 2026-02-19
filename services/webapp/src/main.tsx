import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, NavLink, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import { Plus, Save } from 'lucide-react'
import './styles.css'
import { DashboardPage } from './dashboard/DashboardPage'
import { BillingPage } from './billing/BillingPage'
import { ActionBar } from './components/ActionBar'
import { CapacityBar } from './components/CapacityBar'
import { OsCard } from './components/OsCard'
import { OsDrawer } from './components/OsDrawer'
import { PillToggle } from './components/PillToggle'
import { ToastProvider, useToast } from './components/Toast'
import type { AgendaDay, AgendaWeekResponse, AppSettings, DashboardItem, FilterDefinition, FilterScope, SavedFilter } from './types'

const API = (import.meta.env.VITE_API_BASE?.trim() || 'http://localhost:8000').replace(/\/$/, '')
const STATUS_OPTIONS = ['A', 'AN', 'EN', 'AS', 'AG', 'DS', 'EX', 'F', 'RAG']
const WEEKDAYS: Array<'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun'> = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
const dayLabelFormatter = new Intl.DateTimeFormat('pt-BR', { weekday: 'short' })
const dateFormatter = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })

const toISODate = (date: Date) => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`
const parseISODate = (value: string) => {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, (month || 1) - 1, day || 1)
}
const addDays = (base: string, days: number) => {
  const date = parseISODate(base)
  date.setDate(date.getDate() + days)
  return toISODate(date)
}

const inputBaseClass = "rounded-lg border border-slate-200 bg-white px-3 py-2 text-sm shadow-sm outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100"

function FilterBuilder({ open, value, editingFilter, onClose, onApply, onSave, onUpdate }: { open: boolean; value: FilterDefinition; editingFilter: SavedFilter | null; onClose: () => void; onApply: (filter: FilterDefinition) => void; onSave: (name: string, scope: FilterScope, filter: FilterDefinition) => void; onUpdate: (id: string, name: string, scope: FilterScope, filter: FilterDefinition) => void }) {
  const [draft, setDraft] = useState<FilterDefinition>(value)
  const [assuntosText, setAssuntosText] = useState('')
  const [name, setName] = useState('')
  const [scope, setScope] = useState<FilterScope>('agenda_week')

  useEffect(() => {
    setDraft(value)
    setAssuntosText((value.assunto_ids ?? []).join(','))
    setName(editingFilter?.name ?? '')
    setScope(editingFilter?.scope ?? 'agenda_week')
  }, [value, open, editingFilter])

  if (!open) return null
  const payload = () => ({ ...draft, assunto_ids: assuntosText.split(',').map((x) => x.trim()).filter(Boolean) })

  return <div className="modal-backdrop"><div className="modal-panel"><h3>{editingFilter ? 'Editar filtro' : 'Novo filtro'}</h3>
    <label>Categoria<select value={draft.category ?? ''} onChange={(e) => setDraft({ ...draft, category: (e.target.value || undefined) as FilterDefinition['category'] })}><option value="">(qualquer)</option><option value="instalacao">Instalação</option><option value="manutencao">Manutenção</option><option value="outros">Outros</option></select></label>
    <label>Status<div className="checkbox-row">{STATUS_OPTIONS.map((s) => <label key={s}><input type="checkbox" checked={(draft.status_codes ?? []).includes(s)} onChange={() => setDraft({ ...draft, status_codes: (draft.status_codes ?? []).includes(s) ? (draft.status_codes ?? []).filter((v) => v !== s) : [...(draft.status_codes ?? []), s] })} />{s}</label>)}</div></label>
    <label>Assuntos<input value={assuntosText} onChange={(e) => setAssuntosText(e.target.value)} /></label>
    <label>Nome<input value={name} onChange={(e) => setName(e.target.value)} /></label>
    <label>Escopo<select value={scope} onChange={(e) => setScope(e.target.value as FilterScope)}><option value="agenda_week">Agenda</option><option value="maintenances">Manutenções</option></select></label>
    <div className="actions-row"><button className="btn primary" onClick={() => { onApply(payload()); onClose() }}>Aplicar</button><button className="btn" onClick={() => name && onSave(name, scope, payload())}>Salvar novo</button>{editingFilter && <button className="btn" onClick={() => name && onUpdate(editingFilter.id, name, scope, payload())}>Atualizar</button>}<button className="btn ghost" onClick={onClose}>Fechar</button></div>
  </div></div>
}

function useSavedFilters(scope: FilterScope) {
  const [filters, setFilters] = useState<SavedFilter[]>([])
  const reload = () => fetch(`${API}/filters?scope=${scope}`).then((r) => r.json()).then(setFilters)
  useEffect(() => { reload() }, [scope])
  return { filters, setFilters, reload }
}

function AgendaBoard({ days, startDate, totalDays, loading, selectedFilialId, filialNames }: { days: AgendaDay[]; startDate: string; totalDays: number; loading: boolean; selectedFilialId: '' | '1' | '2'; filialNames: Record<'1' | '2', string> }) {
  const [selected, setSelected] = useState<DashboardItem | null>(null)
  const dates = useMemo(() => Array.from({ length: totalDays }, (_, idx) => addDays(startDate, idx)), [startDate, totalDays])
  const byDate = useMemo(() => Object.fromEntries(days.map((d) => [d.date, d])), [days])
  const today = toISODate(new Date())

  return (
    <section className="panel">
      <header className="panel-header"><h2>Agenda técnica</h2><p>{dateFormatter.format(parseISODate(startDate))} até {dateFormatter.format(parseISODate(addDays(startDate, totalDays - 1)))}</p></header>
      {loading ? <div className="agenda-grid">{dates.map((d) => <div key={d} className="skeleton" />)}</div> : (
        <div className="overflow-x-auto pb-2">
          <div className="flex min-w-max gap-6 snap-x snap-mandatory">
            {dates.map((dayDate) => {
              const day = byDate[dayDate] ?? { date: dayDate, items: [], capacity: { filial_1: { limit: 0, count: 0, remaining: 0, fill_ratio: 0, level: 'green' }, filial_2: { limit: 0, count: 0, remaining: 0, fill_ratio: 0, level: 'green' }, total: { limit: 0, count: 0, remaining: 0, fill_ratio: 0, level: 'green' } } }
              const d = parseISODate(dayDate)
              const isWeekend = [0, 6].includes(d.getDay())
              const isToday = dayDate === today
              const rowClass = isWeekend ? 'bg-amber-50/60' : 'bg-slate-50/80'
              const todayClass = isToday ? 'ring-2 ring-blue-200 border-blue-300' : 'border-slate-200'
              const capacityText = selectedFilialId
                ? `${selectedFilialId === '1' ? filialNames['1'] : filialNames['2']}: ${(selectedFilialId === '1' ? day.capacity.filial_1.count : day.capacity.filial_2.count)}/${(selectedFilialId === '1' ? day.capacity.filial_1.limit : day.capacity.filial_2.limit)}`
                : `F1 ${day.capacity.filial_1.count}/${day.capacity.filial_1.limit} • F2 ${day.capacity.filial_2.count}/${day.capacity.filial_2.limit}`

              return (
                <article key={dayDate} className={`snap-start shrink-0 w-[320px] rounded-2xl border p-3 ${rowClass} ${todayClass}`}>
                  <div className="mb-2 flex items-center justify-between">
                    <h4 className="text-sm font-semibold capitalize">{dayLabelFormatter.format(d)} {dateFormatter.format(d)}</h4>
                    {isToday ? <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs text-blue-700">Hoje</span> : null}
                  </div>
                  <CapacityBar capacity={day.capacity} />
                  <p className="mt-1 text-xs text-slate-600" title={`F1: ${day.capacity.filial_1.count}/${day.capacity.filial_1.limit} (${Math.max(0, day.capacity.filial_1.remaining)} vagas) | F2: ${day.capacity.filial_2.count}/${day.capacity.filial_2.limit} (${Math.max(0, day.capacity.filial_2.remaining)} vagas)`}>{capacityText}</p>
                  <div className="mt-3 space-y-2">
                    {day.items.map((item) => <OsCard key={item.id} item={item} onClick={() => setSelected(item)} />)}
                    {!day.items.length ? <p className="rounded-lg border border-dashed border-slate-300 bg-white/70 p-3 text-xs text-slate-500">Sem OS no dia</p> : null}
                  </div>
                </article>
              )
            })}
          </div>
        </div>
      )}
      <OsDrawer item={selected} open={!!selected} onClose={() => setSelected(null)} />
    </section>
  )
}

function MaintenancesTable({ items, loading, tab, onTab }: { items: DashboardItem[]; loading: boolean; tab: 'open' | 'scheduled' | 'done'; onTab: (t: 'open' | 'scheduled' | 'done') => void }) {
  return <section className="panel"><div className="tab-row"><button className={`btn ${tab === 'open' ? 'primary' : ''}`} onClick={() => onTab('open')}>Abertas</button><button className={`btn ${tab === 'scheduled' ? 'primary' : ''}`} onClick={() => onTab('scheduled')}>Agendadas</button><button className={`btn ${tab === 'done' ? 'primary' : ''}`} onClick={() => onTab('done')}>Finalizadas</button></div>{loading ? <div className="skeleton table-skeleton" /> : <div className="table-wrap"><table><thead><tr><th>Data/Hora</th><th>Cliente</th><th>Bairro/Cidade</th><th>Status</th><th>Protocolo</th></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td>{item.date} {item.time || '--:--'}</td><td>{item.customer_name || '-'}</td><td>{item.bairro || '-'} / {item.cidade || '-'}</td><td>{item.status_label || item.status_code}</td><td>{item.protocolo || '-'}</td></tr>)}</tbody></table></div>}</section>
}

function AgendaPage() {
  const toast = useToast()
  const today = toISODate(new Date())
  const { filters, setFilters } = useSavedFilters('agenda_week')
  const [selectedFilterId, setSelectedFilterId] = useState('')
  const [currentFilter, setCurrentFilter] = useState<FilterDefinition>({ category: 'instalacao' })
  const [builderOpen, setBuilderOpen] = useState(false)
  const [editing, setEditing] = useState<SavedFilter | null>(null)
  const [agendaDays, setAgendaDays] = useState<AgendaDay[]>([])
  const [filialNames, setFilialNames] = useState<Record<'1' | '2', string>>({ '1': 'Grande Vitória', '2': 'João Neiva' })
  const [startDate, setStartDate] = useState(today)
  const [days, setDays] = useState(7)
  const [period, setPeriod] = useState<'today' | '7d' | '14d' | '30d'>('7d')
  const [loading, setLoading] = useState(false)
  const [selectedFilialId, setSelectedFilialId] = useState<'' | '1' | '2'>('')
  const [pendingOpen, setPendingOpen] = useState(false)
  const [pending, setPending] = useState<any[]>([])
  const [pendingTotal, setPendingTotal] = useState(0)
  const [pendingError, setPendingError] = useState<string | null>(null)

  const loadPending = async (filial = selectedFilialId) => {
    setPendingError(null)
    const params = new URLSearchParams({ limit: '200' })
    if (filial) params.set('filial_id', filial)
    if (selectedFilterId) params.set('filter_id', selectedFilterId)
    else if (Object.keys(currentFilter).length) params.set('filter_json', JSON.stringify(currentFilter))
    const url = `${API}/dashboard/installations-pending?${params.toString()}`
    console.info('[AgendaPage] pending URL', { url })
    try {
      const res = await fetch(url)
      const text = await res.text()
      if (!res.ok) throw new Error(`HTTP ${res.status} ${res.statusText}
${text.slice(0, 300)}`)
      const payload = JSON.parse(text)
      setPending(payload.items || [])
      setPendingTotal(payload.total || 0)
    } catch (err: any) {
      setPendingError(err?.message || 'Falha ao carregar pendentes')
    }
  }

  const load = async (filter?: FilterDefinition, filterId?: string, s = startDate, d = days, filial = selectedFilialId, p = period) => {
    const base: Record<string, string> = { start: s, days: String(d), period: p }
    if (filial) base.filial_id = filial
    if (filterId) base.filter_id = filterId
    else base.filter_json = JSON.stringify(filter || currentFilter)

    const params = new URLSearchParams(base)
    setLoading(true)
    try {
      const url = `${API}/dashboard/agenda-week?${params}`
      console.info('[AgendaPage] agenda URL', { url })
      const payload = await fetch(url).then((r) => r.json()) as AgendaWeekResponse
      setAgendaDays(payload.days || [])

      const settingsPayload = await fetch(`${API}/settings`).then((r) => r.json())
      setFilialNames({
        '1': String(settingsPayload?.filiais?.['1'] || 'Filial 1'),
        '2': String(settingsPayload?.filiais?.['2'] || 'Filial 2'),
      })
      await loadPending(filial)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const search = new URLSearchParams(window.location.search)
    if (search.get('open_pending') === 'true') setPendingOpen(true)
    load({ category: 'instalacao' }, '', today, 7, '', '7d')
  }, [])

  const setPeriodAndLoad = (p: 'today' | '7d' | '14d' | '30d') => {
    setPeriod(p)
    let d = days
    let s = startDate
    if (p === 'today') { d = 1; s = today }
    else if (p === '7d') d = 7
    else if (p === '14d') d = 14
    else d = 30
    setDays(d)
    setStartDate(s)
    load(undefined, selectedFilterId || undefined, s, d, selectedFilialId, p)
  }

  const save = async (name: string, scope: FilterScope, definition_json: FilterDefinition) => {
    const f = await fetch(`${API}/filters`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, scope, definition_json }) }).then((r) => r.json()) as SavedFilter
    setFilters((prev) => [f, ...prev])
    toast.success('Filtro salvo com sucesso')
  }
  const update = async (id: string, name: string, scope: FilterScope, definition_json: FilterDefinition) => {
    const u = await fetch(`${API}/filters/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, scope, definition_json }) }).then((r) => r.json()) as SavedFilter
    setFilters((prev) => prev.map((f) => f.id === id ? u : f))
    toast.success('Filtro atualizado com sucesso')
  }

  return <section>
    <header className="topbar"><h2>Agenda</h2><div className="controls-row"><select className={inputBaseClass} value={selectedFilterId} onChange={(e) => { const id = e.target.value; setSelectedFilterId(id); const saved = filters.find((f) => f.id === id) || null; setEditing(saved); if (saved) load(undefined, id); else load(currentFilter) }}><option value="">Sem filtro salvo</option>{filters.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select><button className="btn" onClick={() => { setEditing(null); setBuilderOpen(true) }}><Plus size={14} /> Novo filtro</button>{selectedFilterId && <button className="btn" onClick={() => setBuilderOpen(true)}><Save size={14} /> Salvar/Editar</button>}</div></header>

    <ActionBar
      left={<div className="flex flex-wrap gap-2"><PillToggle active={selectedFilialId === ''} onClick={() => { setSelectedFilialId(''); load(undefined, selectedFilterId || undefined, startDate, days, '') }}>Todas</PillToggle><PillToggle active={selectedFilialId === '1'} onClick={() => { setSelectedFilialId('1'); load(undefined, selectedFilterId || undefined, startDate, days, '1') }}>F1 {filialNames['1']}</PillToggle><PillToggle active={selectedFilialId === '2'} onClick={() => { setSelectedFilialId('2'); load(undefined, selectedFilterId || undefined, startDate, days, '2') }}>F2 {filialNames['2']}</PillToggle></div>}
      center={<div className="flex flex-wrap gap-2"><label>Período<select className={inputBaseClass} value={period} onChange={(e) => setPeriodAndLoad(e.target.value as any)}><option value="today">Hoje</option><option value="7d">7 dias</option><option value="14d">14 dias</option><option value="30d">30 dias</option></select></label><label>Início<input className={inputBaseClass} type="date" value={startDate} onChange={(e) => { const d = e.target.value; setStartDate(d); load(undefined, selectedFilterId || undefined, d, days) }} /></label></div>}
      right={<div className="flex flex-wrap gap-2"><button className="btn" onClick={() => { setPendingOpen((v) => !v); if (!pendingOpen) loadPending() }}>Pendentes {pendingTotal > 0 ? `(${pendingTotal})` : ''}</button></div>}
    />

    {pendingError ? <div className="rounded-2xl border border-rose-200 bg-rose-50 p-3 text-rose-700 text-sm whitespace-pre-wrap">{pendingError}</div> : null}

    {pendingOpen ? <div className="panel mb-3"><h3>Pendentes</h3><div className="grid gap-2">{pending.map((p:any) => <div key={p.id} className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-sm"><div className="font-semibold">{p.cliente} · {p.data_agendada} {p.hora || ''}</div><div>{p.bairro_cidade} · {p.dias_atraso} dias atraso</div></div>)}{pending.length===0?<div className="text-sm text-slate-500">Sem pendentes.</div>:null}</div></div> : null}

    <AgendaBoard days={agendaDays} startDate={startDate} totalDays={days} loading={loading} selectedFilialId={selectedFilialId} filialNames={filialNames} />
    <FilterBuilder open={builderOpen} value={currentFilter} editingFilter={editing} onClose={() => setBuilderOpen(false)} onApply={(f) => { setCurrentFilter(f); setSelectedFilterId(''); load(f) }} onSave={save} onUpdate={update} />
  </section>
}

function MaintenancesPage() {
  const toast = useToast()
  const today = toISODate(new Date())
  const { filters, setFilters } = useSavedFilters('maintenances')
  const [selectedFilterId, setSelectedFilterId] = useState('')
  const [currentFilter, setCurrentFilter] = useState<FilterDefinition>({ category: 'manutencao' })
  const [builderOpen, setBuilderOpen] = useState(false)
  const [editing, setEditing] = useState<SavedFilter | null>(null)
  const [items, setItems] = useState<DashboardItem[]>([])
  const [startDate, setStartDate] = useState(today)
  const [days, setDays] = useState(7)
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState<'open' | 'scheduled' | 'done'>('open')

  const load = async (filter?: FilterDefinition, filterId?: string, s = startDate, d = days, activeTab = tab) => {
    const to = addDays(s, d - 1)
    const params = filterId ? new URLSearchParams({ tab: activeTab, from: s, to, filter_id: filterId }) : new URLSearchParams({ tab: activeTab, from: s, to, filter_json: JSON.stringify({ ...(filter || currentFilter), category: 'manutencao' }) })
    setLoading(true)
    try {
      const payload = await fetch(`${API}/dashboard/maintenances?${params}`).then((r) => r.json()) as DashboardItem[]
      setItems(payload)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load({ category: 'manutencao' }, '', today, 7, 'open') }, [])
  useEffect(() => { load(undefined, selectedFilterId || undefined, startDate, days, tab) }, [tab])

  const save = async (name: string, scope: FilterScope, definition_json: FilterDefinition) => {
    try {
      const f = await fetch(`${API}/filters`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, scope, definition_json }) }).then((r) => r.json()) as SavedFilter
      setFilters((prev) => [f, ...prev])
      toast.success('Filtro salvo com sucesso')
    } catch {
      toast.error('Falha ao salvar filtro')
    }
  }
  const update = async (id: string, name: string, scope: FilterScope, definition_json: FilterDefinition) => {
    try {
      const u = await fetch(`${API}/filters/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, scope, definition_json }) }).then((r) => r.json()) as SavedFilter
      setFilters((prev) => prev.map((f) => f.id === id ? u : f))
      toast.success('Filtro atualizado com sucesso')
    } catch {
      toast.error('Falha ao atualizar filtro')
    }
  }

  return <section><header className="topbar"><h2>Manutenções</h2><div className="controls-row"><select className={inputBaseClass} value={selectedFilterId} onChange={(e) => { const id = e.target.value; setSelectedFilterId(id); const saved = filters.find((f) => f.id === id) || null; setEditing(saved); if (saved) load(undefined, id); else load(currentFilter) }}><option value="">Sem filtro salvo</option>{filters.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select><button className="btn" onClick={() => { setEditing(null); setBuilderOpen(true) }}><Plus size={14} /> Novo filtro</button>{selectedFilterId && <button className="btn" onClick={() => setBuilderOpen(true)}><Save size={14} /> Salvar/Editar</button>}</div></header><div className="controls-row block"><label>Início<input className={inputBaseClass} type="date" value={startDate} onChange={(e) => { const d = e.target.value; setStartDate(d); load(undefined, selectedFilterId || undefined, d, days, tab) }} /></label><label>Dias<select className={inputBaseClass} value={days} onChange={(e) => { const d = Number(e.target.value); setDays(d); load(undefined, selectedFilterId || undefined, startDate, d, tab) }}><option value={7}>7</option><option value={14}>14</option><option value={30}>30</option></select></label></div><MaintenancesTable items={items} loading={loading} tab={tab} onTab={setTab} /><FilterBuilder open={builderOpen} value={currentFilter} editingFilter={editing} onClose={() => setBuilderOpen(false)} onApply={(f) => { setCurrentFilter(f); setSelectedFilterId(''); load(f) }} onSave={save} onUpdate={update} /></section>
}

const AdminOnly = ({ children }: { children: React.ReactNode }) => <>{children}</>

function AdminPage() {
  const toast = useToast()
  const [agendaFilters, setAgendaFilters] = useState<SavedFilter[]>([])
  const [maintFilters, setMaintFilters] = useState<SavedFilter[]>([])
  const [settings, setSettings] = useState<AppSettings | null>(null)

  const loadAll = () => {
    fetch(`${API}/filters?scope=agenda_week`).then((r) => r.json()).then(setAgendaFilters)
    fetch(`${API}/filters?scope=maintenances`).then((r) => r.json()).then(setMaintFilters)
    fetch(`${API}/settings`).then((r) => r.json()).then(setSettings)
  }

  useEffect(() => { loadAll() }, [])

  const removeFilter = async (id: string, scope: FilterScope) => {
    try {
      await fetch(`${API}/filters/${id}`, { method: 'DELETE' })
      if (scope === 'agenda_week') setAgendaFilters((p) => p.filter((f) => f.id !== id))
      else setMaintFilters((p) => p.filter((f) => f.id !== id))
      toast.success('Filtro excluído com sucesso')
    } catch {
      toast.error('Falha ao excluir filtro')
    }
  }

  const saveSettings = async () => {
    if (!settings) return
    try {
      const data = await fetch(`${API}/settings`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settings) }).then((r) => r.json())
      setSettings(data)
      toast.success('Configurações salvas com sucesso')
    } catch (error: any) {
      toast.error(`Falha ao salvar: ${error?.message || 'erro desconhecido'}`)
    }
  }

  if (!settings) return <p>Carregando...</p>

  return <AdminOnly><section><header className="topbar"><h2>Admin</h2><p>Preparado para ACL futura</p></header>
    <div className="panel"><h3>Filtros salvos</h3><h4>Agenda</h4>{agendaFilters.map((f) => <div key={f.id} className="row-between"><span>{f.name}</span><button className="btn" onClick={() => removeFilter(f.id, 'agenda_week')}>Excluir</button></div>)}<h4>Manutenções</h4>{maintFilters.map((f) => <div key={f.id} className="row-between"><span>{f.name}</span><button className="btn" onClick={() => removeFilter(f.id, 'maintenances')}>Excluir</button></div>)}</div>
    <div className="panel"><h3>Filtros padrão</h3><label>Agenda<select value={settings.default_filters.agenda ?? ''} onChange={(e) => setSettings({ ...settings, default_filters: { ...settings.default_filters, agenda: e.target.value || null } })}><option value="">Nenhum</option>{agendaFilters.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select></label><label>Manutenções<select value={settings.default_filters.manutencoes ?? ''} onChange={(e) => setSettings({ ...settings, default_filters: { ...settings.default_filters, manutencoes: e.target.value || null } })}><option value="">Nenhum</option>{maintFilters.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select></label></div>
    <div className="panel"><h3>Grupos de Assuntos</h3>{(['instalacao', 'manutencao', 'outros'] as const).map((k) => <label key={k}>{k}<input value={settings.subject_groups[k].join(',')} onChange={(e) => setSettings({ ...settings, subject_groups: { ...settings.subject_groups, [k]: e.target.value.split(',').map((x) => x.trim()).filter(Boolean) } })} /></label>)}</div>
    <div className="panel"><h3>Filiais</h3><div className="grid-2"><label>Filial 1<input value={settings.filiais['1'] ?? ''} onChange={(e) => setSettings({ ...settings, filiais: { ...settings.filiais, '1': e.target.value } })} /></label><label>Filial 2<input value={settings.filiais['2'] ?? ''} onChange={(e) => setSettings({ ...settings, filiais: { ...settings.filiais, '2': e.target.value } })} /></label></div></div>
    <div className="panel"><h3>Capacidade de Agenda</h3><table className="capacity-table"><thead><tr><th>Dia</th><th>{settings.filiais['1'] || 'Filial 1'}</th><th>{settings.filiais['2'] || 'Filial 2'}</th></tr></thead><tbody>{WEEKDAYS.map((wd, idx) => <tr key={wd}><td>{['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom'][idx]}</td><td><input type="number" min={0} value={settings.agenda_capacity['1'][wd]} onChange={(e) => setSettings({ ...settings, agenda_capacity: { ...settings.agenda_capacity, '1': { ...settings.agenda_capacity['1'], [wd]: Math.max(0, Number(e.target.value) || 0) } } })} /></td><td><input type="number" min={0} value={settings.agenda_capacity['2'][wd]} onChange={(e) => setSettings({ ...settings, agenda_capacity: { ...settings.agenda_capacity, '2': { ...settings.agenda_capacity['2'], [wd]: Math.max(0, Number(e.target.value) || 0) } } })} /></td></tr>)}</tbody></table></div>
    <button className="btn primary" onClick={saveSettings}>Salvar configurações</button>
  </section></AdminOnly>
}

function Layout() {
  return <main className="layout"><aside className="sidebar"><h1>Softhub</h1><nav><NavLink to="/dashboard">Dashboard</NavLink><NavLink to="/agenda">Agenda</NavLink><NavLink to="/manutencoes">Manutenções</NavLink><NavLink to="/billing">Billing</NavLink><NavLink to="/admin">Admin</NavLink></nav></aside><section className="content"><Outlet /></section></main>
}

function AppRoutes() {
  return <BrowserRouter><Routes><Route path="/" element={<Layout />}><Route index element={<Navigate to="/dashboard" replace />} /><Route path="dashboard" element={<DashboardPage apiBase={API} />} /><Route path="agenda" element={<AgendaPage />} /><Route path="manutencoes" element={<MaintenancesPage />} /><Route path="billing" element={<BillingPage apiBase={API} />} /><Route path="admin" element={<AdminPage />} /></Route></Routes></BrowserRouter>
}

createRoot(document.getElementById('root')!).render(<ToastProvider><AppRoutes /></ToastProvider>)
