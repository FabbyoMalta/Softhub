from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel


class ContractInfo(BaseModel):
    id: str | None = None
    status: str | None = None
    status_internet: str | None = None
    situacao_financeira: str | None = None
    pago_ate_data: str | None = None
    id_vendedor: str | None = None
    plano_nome: str | None = None


class BillingOpenItem(BaseModel):
    external_id: str | None = None
    id_contrato: str | None = None
    id_cliente: str | None = None
    due_date: str | None = None
    open_days: int
    amount_open: str | None = None
    amount_total: str | None = None
    payment_type: str | None = None
    contract: ContractInfo


class BillingSummaryOut(BaseModel):
    total_open: int
    over_20_days: int
    oldest_due_date: str | None = None


class BillingOpenResponse(BaseModel):
    summary: BillingSummaryOut
    items: list[BillingOpenItem]


class BillingActionOut(BaseModel):
    action_key: str
    external_id: str


class BillingCaseOut(BaseModel):
    id: str
    external_id: str
    id_cliente: str
    id_contrato: str | None = None
    filial_id: str | None = None
    due_date: date | None = None
    amount_open: Decimal
    open_days: int
    payment_type: str | None = None
    status_case: str
    first_seen_at: datetime
    last_seen_at: datetime
    action_state: str
    last_action_at: datetime | None = None
    ticket_id: str | None = None
    ticket_status: str | None = None
    contract_json: dict | None = None
    client_json: dict | None = None
    contract_missing: bool = False


class BillingCasesSummaryOut(BaseModel):
    total_cases: int
    total_amount_open: Decimal
    oldest_due_date: date | None = None
    by_filial: dict[str, int]


class BillingSyncOut(BaseModel):
    synced: int
    upserted: int
    duration_ms: float
    due_from_used: str
    only_open_used: bool


class BillingEnrichOut(BaseModel):
    updated: int
    duration_ms: float


class BillingTicketDryRunOut(BaseModel):
    case_id: str
    eligible: bool
    warnings: list[str]
    payload: dict | None = None
    validation_error: str | None = None


class BillingBatchFilters(BaseModel):
    status: str | None = 'OPEN'
    filial_id: str | None = None
    min_days: int | None = None
    due_from: str | None = None
    due_to: str | None = None


class BillingTicketBatchIn(BaseModel):
    case_ids: list[str] | None = None
    filters: BillingBatchFilters | None = None
    limit: int | None = 50
    require_confirm: bool | None = None


class BillingTicketBatchDryRunOut(BaseModel):
    count: int
    sample: list[dict]
    warnings: list[str]


class BillingTicketCreateOut(BaseModel):
    already_created: bool
    ticket_id: str


class BillingTicketBatchOut(BaseModel):
    created: int
    skipped: int
    errors: int
    duration_ms: float


class BillingReconcileOut(BaseModel):
    closed: int
    would_close: int
    errors: int
