import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'

type DashboardItem = {
  id: string
  date: string
  time: string | null
  type: 'instalacao' | 'manutencao'
  status: string
  customer_id: string
  customer_name: string
  city: string
  neighborhood: string
  address: string
  source: string
}

type FilterDefinition = {
  types?: string[]
  status?: string[]
  date_range?: { start: string; end: string }
  city_contains?: string
  assunto_contains?: string
}

type SavedFilter = {
  id: string
  name: string
  scope: 'agenda_week' | 'maintenances'
  definition_json: FilterDefinition
  created_at: string
}

const API = 'http://localhost:8000'
const WEEK_DAYS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
const STATUS_OPTIONS = ['aberta', 'agendada', 'finalizada']

function FilterBuilder({
  open,
  value,
  onClose,
  onApply,
  onSave,
}: {
  open: boolean
  value: FilterDefinition
  onClose: () => void
  onApply: (filter: FilterDefinition) => void
  onSave: (name: string, scope: 'agenda_week' | 'maintenances', filter: FilterDefinition) => void
}) {
  const [draft, setDraft] = useState<FilterDefinition>(value)
  const [name, setName] = useState('')
  const [scope, setScope] = useState<'agenda_week' | 'maintenances'>('agenda_week')

  useEffect(() => setDraft(value), [value, open])

  if (!open) return null

  const toggle = (key: 'types' | 'status', entry: string) => {
    const current = draft[key] ?? []
    const next = current.includes(entry) ? current.filter((v) => v !== entry) : [...current, entry]
    setDraft({ ...draft, [key]: next })
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: '#0006', display: 'grid', placeItems: 'center' }}>
      <div style={{ background: '#fff', padding: 16, width: 560 }}>
        <h3>Filtro Dashboard</h3>
        <div>
          <strong>Tipo de OS</strong>
          <label><input type="checkbox" checked={(draft.types ?? []).includes('instalacao')} onChange={() => toggle('types', 'instalacao')} /> Instalação</label>
          <label><input type="checkbox" checked={(draft.types ?? []).includes('manutencao')} onChange={() => toggle('types', 'manutencao')} /> Manutenção</label>
        </div>
        <div>
          <strong>Status</strong>
          {STATUS_OPTIONS.map((st) => (
            <label key={st}><input type="checkbox" checked={(draft.status ?? []).includes(st)} onChange={() => toggle('status', st)} /> {st}</label>
          ))}
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input type="date" value={draft.date_range?.start ?? ''} onChange={(e) => setDraft({ ...draft, date_range: { start: e.target.value, end: draft.date_range?.end ?? e.target.value } })} />
          <input type="date" value={draft.date_range?.end ?? ''} onChange={(e) => setDraft({ ...draft, date_range: { start: draft.date_range?.start ?? e.target.value, end: e.target.value } })} />
        </div>
        <div><input placeholder="Cidade contém" value={draft.city_contains ?? ''} onChange={(e) => setDraft({ ...draft, city_contains: e.target.value })} /></div>
        <div><input placeholder="Assunto contém" value={draft.assunto_contains ?? ''} onChange={(e) => setDraft({ ...draft, assunto_contains: e.target.value })} /></div>
        <hr />
        <div>
          <input placeholder="Nome do filtro" value={name} onChange={(e) => setName(e.target.value)} />
          <select value={scope} onChange={(e) => setScope(e.target.value as 'agenda_week' | 'maintenances')}>
            <option value="agenda_week">Agenda</option>
            <option value="maintenances">Manutenções</option>
          </select>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          <button onClick={() => { onApply(draft); onClose() }}>Aplicar</button>
          <button onClick={() => name && onSave(name, scope, draft)}>Salvar filtro</button>
          <button onClick={onClose}>Fechar</button>
        </div>
      </div>
    </div>
  )
}

function AgendaWeekBoard({ items }: { items: DashboardItem[] }) {
  const grouped = useMemo(() => {
    const map = new Map<string, DashboardItem[]>()
    items.forEach((item) => map.set(item.date, [...(map.get(item.date) ?? []), item]))
    return map
  }, [items])
  const dates = [...new Set(items.map((x) => x.date))].sort()

  return (
    <section>
      <h2>Agenda da semana</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, minmax(120px, 1fr))', gap: 8 }}>
        {dates.slice(0, 7).map((day, idx) => (
          <div key={day} style={{ border: '1px solid #ddd', padding: 8 }}>
            <h4>{WEEK_DAYS[idx % 7]} {day}</h4>
            {(grouped.get(day) ?? []).map((item) => (
              <article key={item.id} style={{ border: '1px solid #aaa', padding: 6, marginBottom: 6 }}>
                <div><strong>{item.type}</strong> · {item.status}</div>
                <div>{item.customer_name}</div>
                <div>{item.city}</div>
              </article>
            ))}
          </div>
        ))}
      </div>
    </section>
  )
}

function MaintenancesPanel({
  items,
  tab,
  onTab,
}: {
  items: DashboardItem[]
  tab: 'abertas' | 'agendadas' | 'todas'
  onTab: (tab: 'abertas' | 'agendadas' | 'todas') => void
}) {
  return (
    <section>
      <h2>Manutenções</h2>
      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={() => onTab('abertas')}>Abertas</button>
        <button onClick={() => onTab('agendadas')}>Agendadas</button>
        <button onClick={() => onTab('todas')}>Todas</button>
      </div>
      <table border={1} cellPadding={6} style={{ width: '100%', marginTop: 8 }}>
        <thead><tr><th>Data</th><th>Cliente</th><th>Cidade</th><th>Status</th></tr></thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id}><td>{item.date}</td><td>{item.customer_name}</td><td>{item.city}</td><td>{item.status}</td></tr>
          ))}
        </tbody>
      </table>
    </section>
  )
}

function App() {
  const [agenda, setAgenda] = useState<DashboardItem[]>([])
  const [maintenances, setMaintenances] = useState<DashboardItem[]>([])
  const [savedFilters, setSavedFilters] = useState<SavedFilter[]>([])
  const [selectedFilterId, setSelectedFilterId] = useState('')
  const [currentFilter, setCurrentFilter] = useState<FilterDefinition>({})
  const [builderOpen, setBuilderOpen] = useState(false)
  const [maintTab, setMaintTab] = useState<'abertas' | 'agendadas' | 'todas'>('agendadas')

  const loadSaved = () => {
    fetch(`${API}/filters?scope=agenda_week`).then((res) => res.json()).then(setSavedFilters)
  }

  const loadDashboard = (filter: FilterDefinition, tab: 'abertas' | 'agendadas' | 'todas' = maintTab) => {
    const maintFilter: FilterDefinition = {
      ...filter,
      status: tab === 'todas' ? filter.status : [tab === 'abertas' ? 'aberta' : 'agendada'],
    }
    const agendaParams = new URLSearchParams({ filter_json: JSON.stringify(filter) })
    const maintParams = new URLSearchParams({ filter_json: JSON.stringify(maintFilter) })
    fetch(`${API}/dashboard/agenda-week?${agendaParams}`).then((res) => res.json()).then(setAgenda)
    fetch(`${API}/dashboard/maintenances?${maintParams}`).then((res) => res.json()).then(setMaintenances)
  }

  useEffect(() => {
    loadSaved()
    loadDashboard({})
  }, [])

  useEffect(() => {
    if (!selectedFilterId) return
    const picked = savedFilters.find((f) => f.id === selectedFilterId)
    if (picked) {
      setCurrentFilter(picked.definition_json)
      loadDashboard(picked.definition_json)
    }
  }, [selectedFilterId, savedFilters])

  const saveFilter = (name: string, scope: 'agenda_week' | 'maintenances', filter: FilterDefinition) => {
    fetch(`${API}/filters`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ name, scope, definition_json: filter }),
    }).then(() => loadSaved())
  }

  return (
    <main style={{ fontFamily: 'sans-serif', margin: 16 }}>
      <h1>Softhub Dashboard</h1>
      <div style={{ display: 'flex', gap: 8, marginBottom: 12 }}>
        <select value={selectedFilterId} onChange={(e) => setSelectedFilterId(e.target.value)}>
          <option value="">Sem filtro salvo</option>
          {savedFilters.map((filter) => <option key={filter.id} value={filter.id}>{filter.name}</option>)}
        </select>
        <button onClick={() => setBuilderOpen(true)}>Novo filtro</button>
        <button onClick={() => saveFilter('Filtro ad-hoc', 'agenda_week', currentFilter)}>Salvar</button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
        <AgendaWeekBoard items={agenda} />
        <MaintenancesPanel
          items={maintenances}
          tab={maintTab}
          onTab={(tab) => {
            setMaintTab(tab)
            loadDashboard(currentFilter, tab)
          }}
        />
      </div>
      <FilterBuilder
        open={builderOpen}
        value={currentFilter}
        onClose={() => setBuilderOpen(false)}
        onApply={(filter) => { setCurrentFilter(filter); loadDashboard(filter) }}
        onSave={saveFilter}
      />
    </main>
  )
}

createRoot(document.getElementById('root')!).render(<App />)
