export type DashboardItem = {
  id: string
  scheduled_at: string | null
  date: string
  time: string | null
  status_code: string
  status_label: string
  assunto_id: string
  type: 'instalacao' | 'manutencao' | 'outros'
  id_cliente?: string
  id_filial?: string
  customer_name: string
  bairro: string
  cidade: string
  protocolo: string
}

export type CapacityEntry = { limit: number; count: number; remaining: number; fill_ratio: number; level: 'green' | 'yellow' | 'red' }
export type DayCapacity = { filial_1: CapacityEntry; filial_2: CapacityEntry; total: CapacityEntry }
export type AgendaDay = { date: string; items: DashboardItem[]; capacity: DayCapacity }
export type AgendaWeekResponse = { days: AgendaDay[] }

export type FilterDefinition = { assunto_ids?: string[]; status_codes?: string[]; category?: 'instalacao' | 'manutencao' | 'outros' }
export type FilterScope = 'agenda_week' | 'maintenances'
export type SavedFilter = { id: string; name: string; scope: FilterScope; definition_json: FilterDefinition; created_at: string }

export type AppSettings = {
  default_filters: { agenda: string | null; manutencoes: string | null }
  installation_subject_ids: string[]
  maintenance_subject_ids: string[]
  subject_groups: { instalacao: string[]; manutencao: string[]; outros: string[] }
  agenda_capacity: Record<'1' | '2', Record<'mon' | 'tue' | 'wed' | 'thu' | 'fri' | 'sat' | 'sun', number>>
  filiais: Record<'1' | '2', string>
}
