import React, { useEffect, useMemo, useState } from 'react'
import { createRoot } from 'react-dom/client'

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
const WEEK_DAYS = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
const OPEN_LIKE = ['A', 'AN', 'EN', 'AS', 'DS', 'EX', 'RAG']
const SCHEDULED = ['AG', 'RAG']
const DONE = ['F']
const STATUS_OPTIONS = ['A', 'AN', 'EN', 'AS', 'AG', 'DS', 'EX', 'F', 'RAG']

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
  const [assuntosText, setAssuntosText] = useState('')
  const [name, setName] = useState('')
  const [scope, setScope] = useState<'agenda_week' | 'maintenances'>('agenda_week')

  useEffect(() => {
    setDraft(value)
    setAssuntosText((value.assunto_ids ?? []).join(','))
  }, [value, open])

  if (!open) return null

  const toggleStatus = (status: string) => {
    const current = draft.status_codes ?? []
    const next = current.includes(status) ? current.filter((v) => v !== status) : [...current, status]
    setDraft({ ...draft, status_codes: next })
  }

  return (
    <div style={{ position: 'fixed', inset: 0, background: '#0006', display: 'grid', placeItems: 'center' }}>
      <div style={{ background: '#fff', padding: 16, width: 620 }}>
        <h3>Filter Builder</h3>
        <div>
          <label>Categoria </label>
          <select value={draft.category ?? ''} onChange={(e) => setDraft({ ...draft, category: (e.target.value || undefined) as any })}>
            <option value="">(qualquer)</option>
            <option value="instalacao">Instalação</option>
            <option value="manutencao">Manutenção</option>
            <option value="outros">Outros</option>
          </select>
        </div>
        <div>
          <strong>Status</strong>
          <div>
            {STATUS_OPTIONS.map((s) => (
              <label key={s} style={{ marginRight: 8 }}>
                <input type="checkbox" checked={(draft.status_codes ?? []).includes(s)} onChange={() => toggleStatus(s)} /> {s}
              </label>
            ))}
          </div>
        </div>
        <div>
          <label>Assuntos (ids separados por vírgula)</label>
          <input
            value={assuntosText}
            onChange={(e) => setAssuntosText(e.target.value)}
            onBlur={() => setDraft({ ...draft, assunto_ids: assuntosText.split(',').map((x) => x.trim()).filter(Boolean) })}
            placeholder="1,17,34"
          />
        </div>
        <hr />
        <div>
          <input placeholder="Nome do filtro" value={name} onChange={(e) => setName(e.target.value)} />
          <select value={scope} onChange={(e) => setScope(e.target.value as 'agenda_week' | 'maintenances')}>
            <option value="agenda_week">Agenda</option>
            <option value="maintenances">Manutenções</option>
          </select>
        </div>
        <div style={{ marginTop: 12, display: 'flex', gap: 8 }}>
          <button onClick={() => { onApply({ ...draft, assunto_ids: assuntosText.split(',').map((x) => x.trim()).filter(Boolean) }); onClose() }}>Aplicar</button>
          <button onClick={() => name && onSave(name, scope, { ...draft, assunto_ids: assuntosText.split(',').map((x) => x.trim()).filter(Boolean) })}>Salvar filtro</button>
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
  const dates = [...new Set(items.map((x) => x.date))].sort().slice(0, 7)

  return (
    <section>
      <h2>Agenda da Semana</h2>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(7, minmax(120px, 1fr))', gap: 8 }}>
        {dates.map((day, idx) => (
          <div key={day} style={{ border: '1px solid #ddd', padding: 8 }}>
            <h4>{WEEK_DAYS[idx]} {day}</h4>
            {(grouped.get(day) ?? []).map((item) => (
              <article key={item.id} style={{ border: '1px solid #aaa', padding: 6, marginBottom: 6 }}>
                <div>{item.time} · <b>{item.status_label}</b></div>
                <div>{item.customer_name}</div>
                <div>{item.bairro}/{item.cidade}</div>
                <div><small>{item.type}</small></div>
              </article>
            ))}
          </div>
        ))}
      </div>
    </section>
  )
}

function MaintenancesPanel({ items }: { items: DashboardItem[] }) {
  const [tab, setTab] = useState<'open' | 'scheduled' | 'done'>('open')
  const filtered = useMemo(() => {
    if (tab === 'open') return items.filter((i) => OPEN_LIKE.includes(i.status_code))
    if (tab === 'scheduled') return items.filter((i) => SCHEDULED.includes(i.status_code))
    return items.filter((i) => DONE.includes(i.status_code))
  }, [items, tab])

  return (
    <section>
      <h2>Manutenções</h2>
      <div style={{ display: 'flex', gap: 8 }}>
        <button onClick={() => setTab('open')}>Abertas/Andamento</button>
        <button onClick={() => setTab('scheduled')}>Agendadas</button>
        <button onClick={() => setTab('done')}>Finalizadas</button>
      </div>
      <table border={1} cellPadding={6} style={{ width: '100%', marginTop: 8 }}>
        <thead><tr><th>Data</th><th>Hora</th><th>Cliente</th><th>Bairro/Cidade</th><th>Status</th></tr></thead>
        <tbody>
          {filtered.map((item) => (
            <tr key={item.id}><td>{item.date}</td><td>{item.time}</td><td>{item.customer_name}</td><td>{item.bairro}/{item.cidade}</td><td>{item.status_label}</td></tr>
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

  const loadSaved = () => {
    fetch(`${API}/filters?scope=agenda_week`).then((res) => res.json()).then(setSavedFilters)
  }

  const loadDashboard = (filter?: FilterDefinition, filterId?: string) => {
    const agendaParams = filterId
      ? new URLSearchParams({ filter_id: filterId })
      : new URLSearchParams({ filter_json: JSON.stringify(filter || {}) })
    const maintParams = filterId
      ? new URLSearchParams({ filter_id: filterId })
      : new URLSearchParams({ filter_json: JSON.stringify({ ...(filter || {}), category: 'manutencao' }) })

    fetch(`${API}/dashboard/agenda-week?${agendaParams}`).then((res) => res.json()).then(setAgenda)
    fetch(`${API}/dashboard/maintenances?${maintParams}`).then((res) => res.json()).then(setMaintenances)
  }

  useEffect(() => {
    if (window.location.pathname !== '/dashboard') {
      window.history.replaceState({}, '', '/dashboard')
    }
    loadSaved()
    loadDashboard({})
  }, [])

  const onSelectSaved = (id: string) => {
    setSelectedFilterId(id)
    if (!id) {
      loadDashboard(currentFilter)
      return
    }
    loadDashboard(undefined, id)
  }

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
        <select value={selectedFilterId} onChange={(e) => onSelectSaved(e.target.value)}>
          <option value="">Sem filtro salvo</option>
          {savedFilters.map((filter) => <option key={filter.id} value={filter.id}>{filter.name}</option>)}
        </select>
        <button onClick={() => setBuilderOpen(true)}>Novo filtro</button>
        <button onClick={() => saveFilter('Filtro ad-hoc', 'agenda_week', currentFilter)}>Salvar</button>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '2fr 1fr', gap: 16 }}>
        <AgendaWeekBoard items={agenda} />
        <MaintenancesPanel items={maintenances} />
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
