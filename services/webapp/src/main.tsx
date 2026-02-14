import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'
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
  id_cliente: string
  customer_name: string
  phone: string
  address: string
  bairro: string
  cidade: string
  protocolo: string
  source: string
}

type FilterDefinition = {
  assunto_ids?: string[]
  status_codes?: string[]
  category?: 'instalacao' | 'manutencao' | 'outros'
}

type SavedFilter = {
  id: string
  name: string
  scope: 'agenda_week' | 'maintenances'
  definition_json: FilterDefinition
  created_at: string
}

const API = 'http://localhost:8000'
const OPEN_LIKE = ['A', 'AN', 'EN', 'AS', 'DS', 'EX', 'RAG']
const SCHEDULED = ['AG', 'RAG']
const DONE = ['F']
const STATUS_OPTIONS = ['A', 'AN', 'EN', 'AS', 'AG', 'DS', 'EX', 'F', 'RAG']

const dayLabelFormatter = new Intl.DateTimeFormat('pt-BR', { weekday: 'short' })
const dateFormatter = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit', year: '2-digit' })

const toISODate = (date: Date) => {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

const parseISODate = (value: string) => {
  const [year, month, day] = value.split('-').map(Number)
  return new Date(year, (month || 1) - 1, day || 1)
}

const addDays = (base: string, days: number) => {
  const date = parseISODate(base)
  date.setDate(date.getDate() + days)
  return toISODate(date)
}

const buildPeriodLabel = (startDate: string, days: number) => {
  const end = addDays(startDate, days - 1)
  return `${dateFormatter.format(parseISODate(startDate))} até ${dateFormatter.format(parseISODate(end))}`
}

const statusBadgeClass = (statusCode: string) => {
  if (DONE.includes(statusCode)) return 'badge success'
  if (SCHEDULED.includes(statusCode)) return 'badge warning'
  if (['EN', 'AS'].includes(statusCode)) return 'badge info'
  return 'badge danger'
}

function FilterBuilder({
  open,
  value,
  editingFilter,
  onClose,
  onApply,
  onSave,
  onUpdate,
}: {
  open: boolean
  value: FilterDefinition
  editingFilter: SavedFilter | null
  onClose: () => void
  onApply: (filter: FilterDefinition) => void
  onSave: (name: string, scope: 'agenda_week' | 'maintenances', filter: FilterDefinition) => void
  onUpdate: (id: string, name: string, scope: 'agenda_week' | 'maintenances', filter: FilterDefinition) => void
}) {
  const [draft, setDraft] = useState<FilterDefinition>(value)
  const [assuntosText, setAssuntosText] = useState('')
  const [name, setName] = useState('')
  const [scope, setScope] = useState<'agenda_week' | 'maintenances'>('agenda_week')

  useEffect(() => {
    setDraft(value)
    setAssuntosText((value.assunto_ids ?? []).join(','))
    if (editingFilter) {
      setName(editingFilter.name)
      setScope(editingFilter.scope)
    } else {
      setName('')
      setScope('agenda_week')
    }
  }, [value, open, editingFilter])

  if (!open) return null

  const buildPayload = () => ({
    ...draft,
    assunto_ids: assuntosText
      .split(',')
      .map((x) => x.trim())
      .filter(Boolean),
  })

  const toggleStatus = (status: string) => {
    const current = draft.status_codes ?? []
    const next = current.includes(status) ? current.filter((v) => v !== status) : [...current, status]
    setDraft({ ...draft, status_codes: next })
  }

  return (
    <div className="modal-backdrop">
      <div className="modal-panel">
        <h3>{editingFilter ? 'Editar filtro salvo' : 'Novo filtro'}</h3>
        <div className="field-row">
          <label>Categoria</label>
          <select
            value={draft.category ?? ''}
            onChange={(e) => {
              const value = e.target.value
              const category = value === '' ? undefined : (value as FilterDefinition['category'])
              setDraft({ ...draft, category })
            }}
          >
            <option value="">(qualquer)</option>
            <option value="instalacao">Instalação</option>
            <option value="manutencao">Manutenção</option>
            <option value="outros">Outros</option>
          </select>
        </div>
        <div className="field-row">
          <label>Status</label>
          <div className="checkbox-row">
            {STATUS_OPTIONS.map((s) => (
              <label key={s}>
                <input type="checkbox" checked={(draft.status_codes ?? []).includes(s)} onChange={() => toggleStatus(s)} /> {s}
              </label>
            ))}
          </div>
        </div>
        <div className="field-row">
          <label>Assuntos (ids separados por vírgula)</label>
          <input
            value={assuntosText}
            onChange={(e) => setAssuntosText(e.target.value)}
            placeholder="1,17,34"
          />
        </div>
        <hr />
        <div className="field-row">
          <label>Nome do filtro</label>
          <input value={name} onChange={(e) => setName(e.target.value)} />
          <select value={scope} onChange={(e) => setScope(e.target.value as 'agenda_week' | 'maintenances')}>
            <option value="agenda_week">Agenda</option>
            <option value="maintenances">Manutenções</option>
          </select>
        </div>
        <div className="actions-row">
          <button
            className="btn primary"
            onClick={() => {
              onApply(buildPayload())
              onClose()
            }}
          >
            Aplicar
          </button>
          <button className="btn" onClick={() => name && onSave(name, scope, buildPayload())}>Salvar novo</button>
          {editingFilter && <button className="btn" onClick={() => name && onUpdate(editingFilter.id, name, scope, buildPayload())}>Atualizar</button>}
          <button className="btn ghost" onClick={onClose}>Fechar</button>
        </div>
      </div>
    </div>
  )
}

function AgendaWeekBoard({ items, startDate, days, loading }: { items: DashboardItem[]; startDate: string; days: number; loading: boolean }) {
  const grouped = useMemo(() => {
    const map = new Map<string, DashboardItem[]>()
    items.forEach((item) => map.set(item.date, [...(map.get(item.date) ?? []), item]))
    return map
  }, [items])

  const dates = useMemo(() => Array.from({ length: days }, (_, idx) => addDays(startDate, idx)), [startDate, days])

  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Agenda técnica</h2>
        <p>Período: {buildPeriodLabel(startDate, days)}</p>
      </header>

      {loading ? (
        <div className="agenda-grid">
          {Array.from({ length: days }).map((_, idx) => <div key={idx} className="skeleton day-skeleton" />)}
        </div>
      ) : (
        <>
          <div className="agenda-grid">
            {dates.map((day) => {
              const date = parseISODate(day)
              const dayLabel = dayLabelFormatter.format(date).replace('.', '')
              const header = `${dayLabel.charAt(0).toUpperCase()}${dayLabel.slice(1)} ${dateFormatter.format(date)}`

              return (
                <article key={day} className="day-card">
                  <h4>{header}</h4>
                  <div className="day-list">
                    {(grouped.get(day) ?? []).map((item) => (
                      <div key={item.id} className="ticket-card">
                        <div className="ticket-head">
                          <strong>{item.time || '--:--'}</strong>
                          <span className={statusBadgeClass(item.status_code)}>{item.status_label || item.status_code}</span>
                        </div>
                        <div className="ticket-customer">{item.customer_name || 'Cliente não informado'}</div>
                        <div className="ticket-meta">{item.bairro || '-'} · {item.cidade || '-'}</div>
                        <div className="ticket-meta">
                          <span className="badge muted">{item.type}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </article>
              )
            })}
          </div>
          {items.length === 0 && <p className="empty">Nenhuma OS encontrada</p>}
        </>
      )}
    </section>
  )
}

function MaintenancesPanel({ items, loading }: { items: DashboardItem[]; loading: boolean }) {
  const [tab, setTab] = useState<'open' | 'scheduled' | 'done'>('open')
  const filtered = useMemo(() => {
    if (tab === 'open') return items.filter((i) => OPEN_LIKE.includes(i.status_code))
    if (tab === 'scheduled') return items.filter((i) => SCHEDULED.includes(i.status_code))
    return items.filter((i) => DONE.includes(i.status_code))
  }, [items, tab])

  return (
    <section className="panel">
      <header className="panel-header">
        <h2>Manutenções</h2>
      </header>
      <div className="tab-row">
        <button className={`btn ${tab === 'open' ? 'primary' : ''}`} onClick={() => setTab('open')}>Abertas</button>
        <button className={`btn ${tab === 'scheduled' ? 'primary' : ''}`} onClick={() => setTab('scheduled')}>Agendadas</button>
        <button className={`btn ${tab === 'done' ? 'primary' : ''}`} onClick={() => setTab('done')}>Finalizadas</button>
      </div>

      {loading ? (
        <div className="skeleton table-skeleton" />
      ) : filtered.length === 0 ? (
        <p className="empty">Nenhuma OS encontrada</p>
      ) : (
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Data</th>
                <th>Hora</th>
                <th>Cliente</th>
                <th>Bairro/Cidade</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((item) => (
                <tr key={item.id}>
                  <td>{dateFormatter.format(parseISODate(item.date))}</td>
                  <td>{item.time || '--:--'}</td>
                  <td>{item.customer_name || '-'}</td>
                  <td>{item.bairro || '-'} / {item.cidade || '-'}</td>
                  <td><span className={statusBadgeClass(item.status_code)}>{item.status_label || item.status_code}</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  )
}

function App() {
  const todayISO = toISODate(new Date())
  const [agenda, setAgenda] = useState<DashboardItem[]>([])
  const [maintenances, setMaintenances] = useState<DashboardItem[]>([])
  const [savedFilters, setSavedFilters] = useState<SavedFilter[]>([])
  const [selectedFilterId, setSelectedFilterId] = useState('')
  const [currentFilter, setCurrentFilter] = useState<FilterDefinition>({})
  const [builderOpen, setBuilderOpen] = useState(false)
  const [editingFilter, setEditingFilter] = useState<SavedFilter | null>(null)
  const [startDate, setStartDate] = useState(todayISO)
  const [days, setDays] = useState(7)
  const [loading, setLoading] = useState(false)

  const loadSaved = () => {
    fetch(`${API}/filters?scope=agenda_week`).then((res) => res.json()).then(setSavedFilters)
  }

  const loadDashboard = (filter?: FilterDefinition, filterId?: string, selectedStart?: string, selectedDays?: number) => {
    const effectiveStart = selectedStart ?? startDate
    const effectiveDays = selectedDays ?? days
    const maintenanceTo = addDays(effectiveStart, effectiveDays - 1)

    const agendaParams = filterId
      ? new URLSearchParams({ start: effectiveStart, days: String(effectiveDays), filter_id: filterId })
      : new URLSearchParams({ start: effectiveStart, days: String(effectiveDays), filter_json: JSON.stringify(filter || {}) })
    const maintParams = filterId
      ? new URLSearchParams({ from: effectiveStart, to: maintenanceTo, filter_id: filterId })
      : new URLSearchParams({ from: effectiveStart, to: maintenanceTo, filter_json: JSON.stringify({ ...(filter || {}), category: 'manutencao' }) })

    setLoading(true)
    Promise.all([
      fetch(`${API}/dashboard/agenda-week?${agendaParams}`).then((res) => res.json()),
      fetch(`${API}/dashboard/maintenances?${maintParams}`).then((res) => res.json()),
    ])
      .then(([agendaData, maintenanceData]) => {
        setAgenda(agendaData)
        setMaintenances(maintenanceData)
      })
      .finally(() => {
        setLoading(false)
      })
  }

  useEffect(() => {
    if (window.location.pathname !== '/dashboard') {
      window.history.replaceState({}, '', '/dashboard')
    }
    loadSaved()
    loadDashboard({}, '', todayISO, 7)
  }, [])

  const onSelectSaved = (id: string) => {
    setSelectedFilterId(id)
    if (!id) {
      setEditingFilter(null)
      loadDashboard(currentFilter)
      return
    }
    const selectedFilter = savedFilters.find((filter) => filter.id === id) ?? null
    setEditingFilter(selectedFilter)
    if (selectedFilter) {
      setCurrentFilter(selectedFilter.definition_json)
    }
    loadDashboard(undefined, id)
  }

  const saveFilter = (name: string, scope: 'agenda_week' | 'maintenances', filter: FilterDefinition) => {
    fetch(`${API}/filters`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, scope, definition_json: filter }),
    }).then((res) => res.json()).then((created: SavedFilter) => setSavedFilters((prev) => [created, ...prev]))
  }

  const updateFilter = (id: string, name: string, scope: 'agenda_week' | 'maintenances', filter: FilterDefinition) => {
    fetch(`${API}/filters/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, scope, definition_json: filter }),
    }).then((res) => res.json()).then((updated: SavedFilter) => {
      setSavedFilters((prev) => prev.map((item) => (item.id === id ? updated : item)))
      setSelectedFilterId(updated.id)
      setEditingFilter(updated)
      setCurrentFilter(updated.definition_json)
    })
  }

  return (
    <main className="layout">
      <aside className="sidebar">
        <h1>Softhub</h1>
        <nav>
          <a href="#">Dashboard</a>
          <a href="#">Agenda</a>
          <a href="#">Manutenções</a>
        </nav>
      </aside>

      <section className="content">
        <header className="topbar">
          <div>
            <h2>Painel Operacional</h2>
            <p>Agenda iniciando em: {dateFormatter.format(parseISODate(startDate))}</p>
          </div>
          <div className="controls-row">
            <select value={selectedFilterId} onChange={(e) => onSelectSaved(e.target.value)}>
              <option value="">Sem filtro salvo</option>
              {savedFilters.map((filter) => (
                <option key={filter.id} value={filter.id}>{filter.name}</option>
              ))}
            </select>
            <button className="btn" onClick={() => { setEditingFilter(null); setBuilderOpen(true) }}>Novo filtro</button>
            {selectedFilterId && <button className="btn" onClick={() => { const selected = savedFilters.find((item) => item.id === selectedFilterId) ?? null; setEditingFilter(selected); if (selected) setCurrentFilter(selected.definition_json); setBuilderOpen(true) }}>Editar filtro</button>}
          </div>
        </header>

        <div className="controls-row block">
          <label>
            Início
            <input
              type="date"
              value={startDate}
              onChange={(e) => {
                const value = e.target.value
                setStartDate(value)
                loadDashboard(selectedFilterId ? undefined : currentFilter, selectedFilterId || undefined, value, days)
              }}
            />
          </label>
          <label>
            Dias
            <select
              value={days}
              onChange={(e) => {
                const value = Number(e.target.value)
                setDays(value)
                loadDashboard(selectedFilterId ? undefined : currentFilter, selectedFilterId || undefined, startDate, value)
              }}
            >
              <option value={7}>7</option>
              <option value={10}>10</option>
              <option value={14}>14</option>
            </select>
          </label>
        </div>

        <div className="dashboard-grid">
          <AgendaWeekBoard items={agenda} startDate={startDate} days={days} loading={loading} />
          <MaintenancesPanel items={maintenances} loading={loading} />
        </div>
      </section>

      <FilterBuilder
        open={builderOpen}
        value={currentFilter}
        editingFilter={editingFilter}
        onClose={() => setBuilderOpen(false)}
        onApply={(filter) => {
          setCurrentFilter(filter)
          loadDashboard(filter)
        }}
        onSave={saveFilter}
        onUpdate={updateFilter}
      />
    </main>
  )
}

createRoot(document.getElementById('root')!).render(<App />)
