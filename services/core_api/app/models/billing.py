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


class BillingCasesSummaryOut(BaseModel):
    total_cases: int
    total_amount_open: Decimal
    oldest_due_date: date | None = None
    by_filial: dict[str, int]
