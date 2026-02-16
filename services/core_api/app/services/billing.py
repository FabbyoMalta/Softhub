from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
import logging
from decimal import Decimal
from typing import Any

from sqlalchemy import select

from app.adapters.ixc_adapter import IXCAdapter
from app.db import BillingAction, SessionLocal
from app.utils.profiling import timer

logger = logging.getLogger(__name__)


@dataclass
class BillingSummary:
    total_open: int
    over_20_days: int
    oldest_due_date: str | None


def _parse_date(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.strptime(raw, '%Y-%m-%d').date()
    except ValueError:
        return None


def _to_decimal(raw: str | None) -> Decimal:
    try:
        return Decimal(raw or '0')
    except Exception:
        return Decimal('0')


def enrich_contas_receber_with_contrato(adapter: IXCAdapter, contas: list[dict[str, Any]]) -> list[dict[str, Any]]:
    today = date.today()
    cache_contratos: dict[str, dict[str, Any]] = {}
    enriched: list[dict[str, Any]] = []

    for conta in contas:
        id_contrato = (conta.get('id_contrato') or '').strip()
        contrato: dict[str, Any] = {}
        contract_missing = False

        if id_contrato:
            if id_contrato not in cache_contratos:
                found = adapter.list_contratos(filters={'id': id_contrato})
                cache_contratos[id_contrato] = found[0] if found else {}
            contrato = cache_contratos[id_contrato]
        else:
            contract_missing = True  # TODO(join-fallback): tentar por id_cliente no futuro.

        due = _parse_date(conta.get('data_vencimento'))
        open_days = 0
        if _to_decimal(conta.get('valor_aberto')) > 0 and due:
            open_days = max(0, (today - due).days)

        enriched.append(
            {
                **conta,
                'contract_missing': contract_missing,
                'contrato_id': contrato.get('id'),
                'contrato_status': contrato.get('status'),
                'status_internet': contrato.get('status_internet'),
                'situacao_financeira_contrato': contrato.get('situacao_financeira_contrato'),
                'pago_ate_data': contrato.get('pago_ate_data'),
                'id_vendedor': contrato.get('id_vendedor'),
                'plano_nome': contrato.get('contrato'),
                'id_cliente': contrato.get('id_cliente') or conta.get('id_cliente'),
                'open_days': open_days,
            }
        )
    return enriched


def mark_action_if_new(action_key: str, external_id: str) -> bool:
    with SessionLocal() as session:
        found = session.scalar(select(BillingAction).where(BillingAction.action_key == action_key))
        if found:
            return False
        session.add(BillingAction(action_key=action_key, external_id=external_id))
        session.commit()
        return True


def list_billing_actions(limit: int = 200) -> list[dict[str, str]]:
    with SessionLocal() as session:
        rows = list(session.scalars(select(BillingAction).limit(limit)))
        return [{'action_key': row.action_key, 'external_id': row.external_id} for row in rows]


def build_billing_open_response(adapter: IXCAdapter) -> dict[str, Any]:
    with timer('billing.total', logger, {'endpoint': 'billing.open'}):
        with timer('billing.fetch_open', logger):
            contas = adapter.list_contas_receber_abertas()
        with timer('billing.enrich_contract', logger, {'records': len(contas)}):
            contas_enriq = enrich_contas_receber_with_contrato(adapter, contas)

        oldest_due: date | None = None
        over_20_days = 0
        items = []

        for item in contas_enriq:
            due = _parse_date(item.get('data_vencimento'))
            if due and (oldest_due is None or due < oldest_due):
                oldest_due = due

            if item['open_days'] >= 20:
                over_20_days += 1
                external_id = str(item.get('id'))
                action_key = f'billing:{external_id}:open_ticket'
                mark_action_if_new(action_key, external_id)

            items.append(
                {
                    'external_id': item.get('id'),
                    'id_contrato': item.get('id_contrato'),
                    'id_cliente': item.get('id_cliente'),
                    'due_date': item.get('data_vencimento'),
                    'open_days': item.get('open_days'),
                    'amount_open': item.get('valor_aberto'),
                    'amount_total': item.get('valor'),
                    'payment_type': item.get('tipo_recebimento'),
                    'contract': {
                        'id': item.get('contrato_id'),
                        'status': item.get('contrato_status'),
                        'status_internet': item.get('status_internet'),
                        'situacao_financeira': item.get('situacao_financeira_contrato'),
                        'pago_ate_data': item.get('pago_ate_data'),
                        'id_vendedor': item.get('id_vendedor'),
                        'plano_nome': item.get('plano_nome'),
                    },
                }
            )

        summary = BillingSummary(
            total_open=len(items),
            over_20_days=over_20_days,
            oldest_due_date=oldest_due.strftime('%Y-%m-%d') if oldest_due else None,
        )
        return {'summary': summary.__dict__, 'items': items}
