import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, NavLink, Navigate, Outlet, Route, Routes } from 'react-router-dom'
import './styles.css'

type DashboardItem = {
  id: string
  scheduled_at: string | null
  date: string
  time: string | null
  status_code: string
  status_label: string
  assunto_id: string
  type: 'instalacao' | 'manutencao' | 'outros'
  customer_name: string
  bairro: string
  cidade: string
  protocolo: string
}

type FilterDefinition = {
  assunto_ids?: string[]
  status_codes?: string[]
  category?: 'instalacao' | 'manutencao' | 'outros'
}

type FilterScope = 'agenda_week' | 'maintenances'

type SavedFilter = {
  id: string
  name: string
  scope: FilterScope
  definition_json: FilterDefinition
  created_at: string
}

type AppSettings = {
  default_filters: {
    agenda: string | null
    manutencoes: string | null
  }
  subject_groups: {
    instalacao: string[]
    manutencao: string[]
    outros: string[]
  }
}

type DashboardSummary = {
  period: { start: string; end: string }
  instalacoes: { agendadas_hoje: number; finalizadas_hoje: number; total_periodo: number }
  manutencoes: { abertas_total: number; abertas_hoje: number; finalizadas_hoje: number; total_periodo: number }
}

const API = 'http://localhost:8000'
const OPEN_LIKE = ['A', 'AN', 'EN', 'AS', 'DS', 'EX', 'RAG']
const SCHEDULED = ['AG', 'RAG']
const DONE = ['F']
const STATUS_OPTIONS = ['A', 'AN', 'EN', 'AS', 'AG', 'DS', 'EX', 'F', 'RAG']
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
const buildPeriodLabel = (startDate: string, days: number) => `${dateFormatter.format(parseISODate(startDate))} até ${dateFormatter.format(parseISODate(addDays(startDate, days - 1)))}`
const statusBadgeClass = (statusCode: string) => DONE.includes(statusCode) ? 'badge success' : SCHEDULED.includes(statusCode) ? 'badge warning' : ['EN', 'AS'].includes(statusCode) ? 'badge info' : 'badge danger'

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

function PeriodControls({ startDate, days, onStartDate, onDays }: { startDate: string; days: number; onStartDate: (d: string) => void; onDays: (d: number) => void }) {
  return <div className="controls-row block"><label>Início<input type="date" value={startDate} onChange={(e) => onStartDate(e.target.value)} /></label><label>Dias<select value={days} onChange={(e) => onDays(Number(e.target.value))}><option value={7}>7</option><option value={10}>10</option><option value={14}>14</option></select></label></div>
}

function AgendaBoard({ items, startDate, days, loading }: { items: DashboardItem[]; startDate: string; days: number; loading: boolean }) {
  const grouped = useMemo(() => items.reduce((acc, i) => ({ ...acc, [i.date]: [...(acc[i.date] ?? []), i] }), {} as Record<string, DashboardItem[]>), [items])
  const dates = useMemo(() => Array.from({ length: days }, (_, idx) => addDays(startDate, idx)), [startDate, days])
  return <section className="panel"><header className="panel-header"><h2>Agenda técnica</h2><p>{buildPeriodLabel(startDate, days)}</p></header>{loading ? <div className="agenda-grid">{dates.map((d) => <div key={d} className="skeleton day-skeleton" />)}</div> : <div className="agenda-grid">{dates.map((day) => <article key={day} className="day-card"><h4>{dayLabelFormatter.format(parseISODate(day))} {dateFormatter.format(parseISODate(day))}</h4><div className="day-list">{(grouped[day] ?? []).map((item) => <div key={item.id} className="ticket-card"><div className="ticket-head"><strong>{item.time || '--:--'}</strong><span className={statusBadgeClass(item.status_code)}>{item.status_label || item.status_code}</span></div><div>{item.customer_name || 'Cliente não informado'}</div><small>{item.bairro || '-'} · {item.cidade || '-'}</small></div>)}</div></article>)}</div>}</section>
}

function MaintenancesTable({ items, loading, tab, onTab }: { items: DashboardItem[]; loading: boolean; tab: 'open' | 'scheduled' | 'done'; onTab: (t: 'open' | 'scheduled' | 'done') => void }) {
  const [selected, setSelected] = useState<DashboardItem | null>(null)
  return <section className="panel"><header className="panel-header"><h2>Manutenções</h2></header>
    <div className="tab-row"><button className={`btn ${tab === 'open' ? 'primary' : ''}`} onClick={() => onTab('open')}>Abertas/Andamento</button><button className={`btn ${tab === 'scheduled' ? 'primary' : ''}`} onClick={() => onTab('scheduled')}>Agendadas</button><button className={`btn ${tab === 'done' ? 'primary' : ''}`} onClick={() => onTab('done')}>Finalizadas</button></div>
    {loading ? <div className="skeleton table-skeleton" /> : <div className="table-wrap"><table><thead><tr><th>Data</th><th>Cliente</th><th>Status</th><th /></tr></thead><tbody>{items.map((item) => <tr key={item.id}><td>{item.date ? dateFormatter.format(parseISODate(item.date)) : '-'}</td><td>{item.customer_name || '-'}</td><td><span className={statusBadgeClass(item.status_code)}>{item.status_label || item.status_code}</span></td><td><button className="btn" onClick={() => setSelected(item)}>Detalhes</button></td></tr>)}</tbody></table></div>}
    {selected && <div className="modal-backdrop" onClick={() => setSelected(null)}><div className="modal-panel" onClick={(e) => e.stopPropagation()}><h3>OS {selected.id}</h3><p>Cliente: {selected.customer_name}</p><p>Protocolo: {selected.protocolo || '-'}</p><p>Local: {selected.bairro} / {selected.cidade}</p><button className="btn ghost" onClick={() => setSelected(null)}>Fechar</button></div></div>}
  </section>
}

function useSavedFilters(scope: FilterScope) {
  const [filters, setFilters] = useState<SavedFilter[]>([])
  const reload = () => fetch(`${API}/filters?scope=${scope}`).then((r) => r.json()).then(setFilters)
  useEffect(() => { reload() }, [scope])
  return { filters, setFilters, reload }
}

function DashboardPage() {
  const today = toISODate(new Date())
  const [startDate, setStartDate] = useState(today)
  const [days, setDays] = useState(7)
  const [summary, setSummary] = useState<DashboardSummary | null>(null)
  useEffect(() => { fetch(`${API}/dashboard/summary?${new URLSearchParams({ start: startDate, days: String(days) })}`).then((r) => r.json()).then(setSummary) }, [startDate, days])
  return <section><header className="topbar"><h2>Dashboard</h2><p>Apenas indicadores sumarizados</p></header><PeriodControls startDate={startDate} days={days} onStartDate={setStartDate} onDays={setDays} /><div className="kpi-grid">{summary && [
    ['Inst. agendadas hoje', summary.instalacoes.agendadas_hoje],
    ['Inst. finalizadas hoje', summary.instalacoes.finalizadas_hoje],
    ['Inst. total período', summary.instalacoes.total_periodo],
    ['Manut. abertas total', summary.manutencoes.abertas_total],
    ['Manut. abertas hoje', summary.manutencoes.abertas_hoje],
    ['Manut. finalizadas hoje', summary.manutencoes.finalizadas_hoje],
    ['Total OS período', summary.instalacoes.total_periodo + summary.manutencoes.total_periodo],
  ].map(([label, value]) => <article key={label as string} className="card"><h4>{label}</h4><p>{value as number}</p><span className="badge muted">{summary.period.start} → {summary.period.end}</span></article>)}</div></section>
}

function AgendaPage() {
  const today = toISODate(new Date())
  const { filters, setFilters } = useSavedFilters('agenda_week')
  const [selectedFilterId, setSelectedFilterId] = useState('')
  const [currentFilter, setCurrentFilter] = useState<FilterDefinition>({})
  const [builderOpen, setBuilderOpen] = useState(false)
  const [editing, setEditing] = useState<SavedFilter | null>(null)
  const [items, setItems] = useState<DashboardItem[]>([])
  const [startDate, setStartDate] = useState(today)
  const [days, setDays] = useState(7)
  const [loading, setLoading] = useState(false)
  const load = (filter?: FilterDefinition, filterId?: string, s = startDate, d = days) => {
    const params = filterId ? new URLSearchParams({ start: s, days: String(d), filter_id: filterId }) : new URLSearchParams({ start: s, days: String(d), filter_json: JSON.stringify(filter || currentFilter) })
    setLoading(true)
    fetch(`${API}/dashboard/agenda-week?${params}`).then((r) => r.json()).then(setItems).finally(() => setLoading(false))
  }
  useEffect(() => { load({}, '', today, 7) }, [])
  const save = (name: string, scope: FilterScope, definition_json: FilterDefinition) => fetch(`${API}/filters`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, scope, definition_json }) }).then((r) => r.json()).then((f: SavedFilter) => setFilters((prev) => [f, ...prev]))
  const update = (id: string, name: string, scope: FilterScope, definition_json: FilterDefinition) => fetch(`${API}/filters/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, scope, definition_json }) }).then((r) => r.json()).then((u: SavedFilter) => setFilters((prev) => prev.map((f) => f.id === id ? u : f)))
  return <section><header className="topbar"><h2>Agenda</h2><div className="controls-row"><select value={selectedFilterId} onChange={(e) => { const id = e.target.value; setSelectedFilterId(id); const saved = filters.find((f) => f.id === id) || null; setEditing(saved); if (saved) { setCurrentFilter(saved.definition_json); load(undefined, id) } else load(currentFilter) }}><option value="">Sem filtro salvo</option>{filters.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select><button className="btn" onClick={() => { setEditing(null); setBuilderOpen(true) }}>Novo filtro</button>{selectedFilterId && <button className="btn" onClick={() => setBuilderOpen(true)}>Salvar/Editar</button>}</div></header><PeriodControls startDate={startDate} days={days} onStartDate={(d) => { setStartDate(d); load(undefined, selectedFilterId || undefined, d, days) }} onDays={(d) => { setDays(d); load(undefined, selectedFilterId || undefined, startDate, d) }} /><AgendaBoard items={items} startDate={startDate} days={days} loading={loading} /><FilterBuilder open={builderOpen} value={currentFilter} editingFilter={editing} onClose={() => setBuilderOpen(false)} onApply={(f) => { setCurrentFilter(f); setSelectedFilterId(''); load(f) }} onSave={save} onUpdate={update} /></section>
}

function MaintenancesPage() {
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
  const [mode, setMode] = useState<'queue' | 'period'>('queue')

  const load = (filter?: FilterDefinition, filterId?: string, s = startDate, d = days, activeTab = tab, activeMode = mode) => {
    const to = addDays(s, d - 1)
    const params = filterId
      ? new URLSearchParams({ tab: activeTab, ...(activeMode === 'period' ? { from: s, to } : {}), filter_id: filterId })
      : new URLSearchParams({ tab: activeTab, ...(activeMode === 'period' ? { from: s, to } : {}), filter_json: JSON.stringify({ ...(filter || currentFilter), category: 'manutencao' }) })
    setLoading(true)
    fetch(`${API}/dashboard/maintenances?${params}`).then((r) => r.json()).then(setItems).finally(() => setLoading(false))
  }
  useEffect(() => { load({ category: 'manutencao' }, '', today, 7) }, [])
  const save = (name: string, scope: FilterScope, definition_json: FilterDefinition) => fetch(`${API}/filters`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, scope, definition_json }) }).then((r) => r.json()).then((f: SavedFilter) => setFilters((prev) => [f, ...prev]))
  const update = (id: string, name: string, scope: FilterScope, definition_json: FilterDefinition) => fetch(`${API}/filters/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, scope, definition_json }) }).then((r) => r.json()).then((u: SavedFilter) => setFilters((prev) => prev.map((f) => f.id === id ? u : f)))
  return <section><header className="topbar"><h2>Manutenções</h2><div className="controls-row"><select value={selectedFilterId} onChange={(e) => { const id = e.target.value; setSelectedFilterId(id); const saved = filters.find((f) => f.id === id) || null; setEditing(saved); if (saved) load(undefined, id); else load(currentFilter) }}><option value="">Sem filtro salvo</option>{filters.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select><button className="btn" onClick={() => { setEditing(null); setBuilderOpen(true) }}>Novo filtro</button>{selectedFilterId && <button className="btn" onClick={() => setBuilderOpen(true)}>Salvar/Editar</button>}</div></header><PeriodControls startDate={startDate} days={days} onStartDate={(d) => { setStartDate(d); load(undefined, selectedFilterId || undefined, d, days) }} onDays={(d) => { setDays(d); load(undefined, selectedFilterId || undefined, startDate, d) }} /><MaintenancesTable items={items} loading={loading} /><FilterBuilder open={builderOpen} value={currentFilter} editingFilter={editing} onClose={() => setBuilderOpen(false)} onApply={(f) => { setCurrentFilter(f); setSelectedFilterId(''); load(f) }} onSave={save} onUpdate={update} /></section>
}

  useEffect(() => { load({ category: 'manutencao' }, '', today, 7, 'open', 'queue') }, [])
  useEffect(() => { load(undefined, selectedFilterId || undefined, startDate, days, tab, mode) }, [tab, mode])

  const save = (name: string, scope: FilterScope, definition_json: FilterDefinition) => fetch(`${API}/filters`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, scope, definition_json }) }).then((r) => r.json()).then((f: SavedFilter) => setFilters((prev) => [f, ...prev]))
  const update = (id: string, name: string, scope: FilterScope, definition_json: FilterDefinition) => fetch(`${API}/filters/${id}`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ name, scope, definition_json }) }).then((r) => r.json()).then((u: SavedFilter) => setFilters((prev) => prev.map((f) => f.id === id ? u : f)))

  return <section><header className="topbar"><h2>Manutenções</h2><div className="controls-row"><select value={selectedFilterId} onChange={(e) => { const id = e.target.value; setSelectedFilterId(id); const saved = filters.find((f) => f.id === id) || null; setEditing(saved); if (saved) load(undefined, id); else load(currentFilter) }}><option value="">Sem filtro salvo</option>{filters.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select><select value={mode} onChange={(e) => setMode(e.target.value as 'queue' | 'period')}><option value="queue">Fila (todas abertas)</option><option value="period">Por período</option></select><button className="btn" onClick={() => { setEditing(null); setBuilderOpen(true) }}>Novo filtro</button>{selectedFilterId && <button className="btn" onClick={() => setBuilderOpen(true)}>Salvar/Editar</button>}</div></header>{mode === 'period' && <PeriodControls startDate={startDate} days={days} onStartDate={(d) => { setStartDate(d); load(undefined, selectedFilterId || undefined, d, days, tab, mode) }} onDays={(d) => { setDays(d); load(undefined, selectedFilterId || undefined, startDate, d, tab, mode) }} />}<MaintenancesTable items={items} loading={loading} tab={tab} onTab={setTab} /><FilterBuilder open={builderOpen} value={currentFilter} editingFilter={editing} onClose={() => setBuilderOpen(false)} onApply={(f) => { setCurrentFilter(f); setSelectedFilterId(''); load(f) }} onSave={save} onUpdate={update} /></section>
}

const AdminOnly = ({ children }: { children: React.ReactNode }) => <>{children}</>

function AdminPage() {
  const [agendaFilters, setAgendaFilters] = useState<SavedFilter[]>([])
  const [maintFilters, setMaintFilters] = useState<SavedFilter[]>([])
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const loadAll = () => {
    fetch(`${API}/filters?scope=agenda_week`).then((r) => r.json()).then(setAgendaFilters)
    fetch(`${API}/filters?scope=maintenances`).then((r) => r.json()).then(setMaintFilters)
    fetch(`${API}/settings`).then((r) => r.json()).then(setSettings)
  }
  useEffect(() => { loadAll() }, [])
  const removeFilter = (id: string, scope: FilterScope) => fetch(`${API}/filters/${id}`, { method: 'DELETE' }).then(() => scope === 'agenda_week' ? setAgendaFilters((p) => p.filter((f) => f.id !== id)) : setMaintFilters((p) => p.filter((f) => f.id !== id)))
  const saveSettings = () => settings && fetch(`${API}/settings`, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(settings) }).then((r) => r.json()).then(setSettings)
  if (!settings) return <p>Carregando...</p>
  return <AdminOnly><section><header className="topbar"><h2>Admin</h2><p>Preparado para ACL futura</p></header>
    <div className="panel"><h3>Filtros salvos</h3><h4>Agenda</h4>{agendaFilters.map((f) => <div key={f.id} className="row-between"><span>{f.name}</span><button className="btn" onClick={() => removeFilter(f.id, 'agenda_week')}>Excluir</button></div>)}<h4>Manutenções</h4>{maintFilters.map((f) => <div key={f.id} className="row-between"><span>{f.name}</span><button className="btn" onClick={() => removeFilter(f.id, 'maintenances')}>Excluir</button></div>)}</div>
    <div className="panel"><h3>Filtros padrão</h3><label>Agenda<select value={settings.default_filters.agenda ?? ''} onChange={(e) => setSettings({ ...settings, default_filters: { ...settings.default_filters, agenda: e.target.value || null } })}><option value="">Nenhum</option>{agendaFilters.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select></label><label>Manutenções<select value={settings.default_filters.manutencoes ?? ''} onChange={(e) => setSettings({ ...settings, default_filters: { ...settings.default_filters, manutencoes: e.target.value || null } })}><option value="">Nenhum</option>{maintFilters.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}</select></label></div>
    <div className="panel"><h3>Grupos de Assuntos</h3>{(['instalacao', 'manutencao', 'outros'] as const).map((k) => <label key={k}>{k}<input value={settings.subject_groups[k].join(',')} onChange={(e) => setSettings({ ...settings, subject_groups: { ...settings.subject_groups, [k]: e.target.value.split(',').map((x) => x.trim()).filter(Boolean) } })} /></label>)}</div>
    <button className="btn primary" onClick={saveSettings}>Salvar configurações</button>
  </section></AdminOnly>
}

function Layout() {
  return <main className="layout"><aside className="sidebar"><h1>Softhub</h1><nav><NavLink to="/dashboard">Dashboard</NavLink><NavLink to="/agenda">Agenda</NavLink><NavLink to="/manutencoes">Manutenções</NavLink><NavLink to="/admin">Admin</NavLink></nav></aside><section className="content"><Outlet /></section></main>
}

function AppRoutes() {
  return <BrowserRouter><Routes><Route path="/" element={<Layout />}><Route index element={<Navigate to="/dashboard" replace />} /><Route path="dashboard" element={<DashboardPage />} /><Route path="agenda" element={<AgendaPage />} /><Route path="manutencoes" element={<MaintenancesPage />} /><Route path="admin" element={<AdminPage />} /></Route></Routes></BrowserRouter>
}

createRoot(document.getElementById('root')!).render(<AppRoutes />)
