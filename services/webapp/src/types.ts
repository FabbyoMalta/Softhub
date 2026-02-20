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

export type BillingContractInfo = {
  id: string | null
  status: string | null
  status_internet: string | null
  situacao_financeira: string | null
  pago_ate_data: string | null
  id_vendedor: string | null
  plano_nome: string | null
}

export type BillingOpenItem = {
  external_id: string | null
  id_contrato: string | null
  id_cliente: string | null
  due_date: string | null
  open_days: number
  amount_open: string | null
  amount_total: string | null
  payment_type: string | null
  contract: BillingContractInfo
}

export type BillingOpenResponse = {
  summary: {
    total_open: number
    over_20_days: number
    oldest_due_date: string | null
  }
  items: BillingOpenItem[]
}

export type BillingAction = {
  action_key: string
  external_id: string
}


export type BillingCase = {
  id: string
  external_id: string
  id_cliente: string
  id_contrato: string | null
  filial_id: string | null
  due_date: string | null
  amount_open: string
  open_days: number
  payment_type: string | null
  status_case: string
  first_seen_at: string
  last_seen_at: string
  action_state: string
  last_action_at: string | null
  ticket_id: string | null
  ticket_status: string | null
  contract_json: Record<string, unknown> | null
  client_json: Record<string, unknown> | null
  contract_missing: boolean
}

export type BillingTicketBatchBody = {
  case_ids?: string[]
  filters?: {
    status?: string
    filial_id?: string
    min_days?: number
    due_from?: string
    due_to?: string
  }
  limit?: number
  require_confirm?: boolean
}
