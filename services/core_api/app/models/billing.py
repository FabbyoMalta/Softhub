from __future__ import annotations

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
