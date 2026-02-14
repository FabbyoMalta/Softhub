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
    <div style={{ position: 'fixed', inset: 0, background: '#0006', display: 'grid', placeItems: 'center' }}>
      <div style={{ background: '#fff', padding: 16, width: 620 }}>
        <h3>{editingFilter ? 'Editar filtro' : 'Filter Builder'}</h3>
        <div>
          <label>Categoria </label>
          <select value={draft.category ?? ''} onChange={(e) => setDraft({ ...draft, category: (e.target.value || undefined) as any })}>
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
        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          <button
            onClick={() => {
              onApply(buildPayload())
              onClose()
            }}
          >
            Aplicar
          </button>
          <button onClick={() => name && onSave(name, scope, buildPayload())}>Salvar novo</button>
          {editingFilter && <button onClick={() => name && onUpdate(editingFilter.id, name, scope, buildPayload())}>Atualizar</button>}
          <button onClick={onClose}>Fechar</button>
        </div>
      </div>
    </div>
  )
}

function AgendaWeekBoard({ items, startDate, days }: { items: DashboardItem[]; startDate: string; days: number }) {
  const grouped = useMemo(() => {
    const map = new Map<string, DashboardItem[]>()
    items.forEach((item) => map.set(item.date, [...(map.get(item.date) ?? []), item]))
    return map
  }, [items])

  const dates = useMemo(() => {
    return Array.from({ length: days }, (_, idx) => addDays(startDate, idx))
  }, [startDate, days])

  return (
    <section>
      <h2>Agenda da Semana</h2>
      <p>Agenda iniciando em: {dateFormatter.format(parseISODate(startDate))}</p>
      <div style={{ display: 'grid', gridTemplateColumns: `repeat(${days}, minmax(120px, 1fr))`, gap: 8 }}>
        {dates.map((day) => {
          const date = parseISODate(day)
          const dayLabel = dayLabelFormatter.format(date).replace('.', '')
          const header = `${dayLabel.charAt(0).toUpperCase()}${dayLabel.slice(1)} ${dateFormatter.format(date)}`

          return (
            <div key={day} style={{ border: '1px solid #ddd', padding: 8 }}>
              <h4>{header}</h4>
              {(grouped.get(day) ?? []).map((item) => (
                <article key={item.id} style={{ border: '1px solid #aaa', padding: 6, marginBottom: 6 }}>
                  <div>
                    {item.time} · <b>{item.status_label}</b>
                  </div>
                  <div>{item.customer_name}</div>
                  <div>
                    {item.bairro}/{item.cidade}
                  </div>
                  <div>
                    <small>{item.type}</small>
                  </div>
                </article>
              ))}
            </div>
          )
        })}
      </div>
      {items.length === 0 && <p>Nenhuma OS encontrada no período.</p>}
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
      {filtered.length === 0 ? (
        <p>Nenhuma OS encontrada no período.</p>
      ) : (
        <table border={1} cellPadding={6} style={{ width: '100%', marginTop: 8 }}>
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
                <td>{item.time}</td>
                <td>{item.customer_name}</td>
                <td>
                  {item.bairro}/{item.cidade}
                </td>
                <td>{item.status_label}</td>
              </tr>
            ))}
          </tbody>
        </table>
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
    try {
      const [agendaRes, maintRes] = await Promise.all([
        fetch(`${API}/dashboard/agenda-week?${agendaParams}`),
        fetch(`${API}/dashboard/maintenances?${maintParams}`),
      ])
      setAgenda(await agendaRes.json())
      setMaintenances(await maintRes.json())
    } finally {
      setLoading(false)
    }
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
    })
      .then((res) => res.json())
      .then((created: SavedFilter) => {
        setSavedFilters((prev) => [created, ...prev])
      })
  }

  const updateFilter = (id: string, name: string, scope: 'agenda_week' | 'maintenances', filter: FilterDefinition) => {
    fetch(`${API}/filters/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, scope, definition_json: filter }),
    })
      .then((res) => res.json())
      .then((updated: SavedFilter) => {
        setSavedFilters((prev) => prev.map((item) => (item.id === id ? updated : item)))
        setSelectedFilterId(updated.id)
        setEditingFilter(updated)
        setCurrentFilter(updated.definition_json)
      })
  }

  return (
    <main style={{ fontFamily: 'sans-serif', margin: 16 }}>
      <h1>Softhub Dashboard</h1>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center', flexWrap: 'wrap' }}>
        <select value={selectedFilterId} onChange={(e) => onSelectSaved(e.target.value)}>
          <option value="">Sem filtro salvo</option>
          {savedFilters.map((filter) => (
            <option key={filter.id} value={filter.id}>
              {filter.name}
            </option>
          ))}
        </select>
        <button
          onClick={() => {
            setEditingFilter(null)
            setBuilderOpen(true)
          }}
        >
          Novo filtro
        </button>
        {selectedFilterId && (
          <button
            onClick={() => {
              const selected = savedFilters.find((item) => item.id === selectedFilterId)
              if (!selected) return
              setEditingFilter(selected)
              setCurrentFilter(selected.definition_json)
              setBuilderOpen(true)
            }}
          >
            Editar filtro
          </button>
        )}
        <button onClick={() => saveFilter('Filtro ad-hoc', 'agenda_week', currentFilter)}>Salvar</button>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 12, alignItems: 'center' }}>
        <label>
          Início:{' '}
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
          Dias:{' '}
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

      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
        <AgendaWeekBoard items={agenda} startDate={startDate} days={days} />
        <MaintenancesPanel items={maintenances} />
      </div>
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
