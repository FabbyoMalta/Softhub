from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from time import perf_counter
from typing import Any

from sqlalchemy import select

from app.adapters.ixc_adapter import IXCAdapter
from app.db import BillingCase, SessionLocal


@dataclass
class BillingSyncResult:
    synced: int
    upserted: int
    duration_ms: float


def _parse_date(raw: Any) -> date | None:
    value = str(raw or '').strip()
    if not value or value == '0000-00-00':
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def _parse_decimal(raw: Any) -> Decimal:
    try:
        return Decimal(str(raw or '0'))
    except Exception:
        return Decimal('0')


def sync_billing_cases(
    adapter: IXCAdapter,
    min_days: int = 20,
    due_from: date | None = None,
    due_to: date | None = None,
    filial_id: str | None = None,
) -> BillingSyncResult:
    started_at = perf_counter()
    now = datetime.utcnow()
    today = date.today()
    rows = adapter.list_contas_receber_atrasadas(
        min_days=min_days,
        due_from=due_from,
        due_to=due_to,
        filial_id=filial_id,
    )

    upserted = 0

    with SessionLocal() as db:
        for row in rows:
            external_id = str(row.get('id') or '').strip()
            id_cliente = str(row.get('id_cliente') or '').strip()
            if not external_id or not id_cliente:
                continue

            amount_open = _parse_decimal(row.get('valor_aberto'))
            due_date = _parse_date(row.get('data_vencimento'))
            if amount_open <= 0 or due_date is None:
                continue

            open_days = max(0, (today - due_date).days)
            if open_days < max(min_days, 0):
                continue

            existing = db.scalar(select(BillingCase).where(BillingCase.external_id == external_id))
            if existing is None:
                existing = BillingCase(
                    external_id=external_id,
                    id_cliente=id_cliente,
                    first_seen_at=now,
                )
                db.add(existing)

            existing.id_cliente = id_cliente
            existing.filial_id = (str(row.get('filial_id') or '').strip() or None)
            existing.due_date = due_date
            existing.amount_open = amount_open
            existing.payment_type = (str(row.get('tipo_recebimento') or '').strip() or None)
            existing.open_days = open_days
            existing.status_case = 'OPEN'
            existing.last_seen_at = now
            existing.snapshot_json = {
                'id_contrato': row.get('id_contrato'),
                'id_contrato_avulso': row.get('id_contrato_avulso'),
                'status': row.get('status'),
                'valor': row.get('valor'),
            }
            upserted += 1

        db.commit()

    return BillingSyncResult(
        synced=len(rows),
        upserted=upserted,
        duration_ms=round((perf_counter() - started_at) * 1000, 2),
    )
