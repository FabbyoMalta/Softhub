from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from time import perf_counter
from typing import Any

from sqlalchemy import and_, select

from app.adapters.ixc_adapter import IXCAdapter
from app.config import get_settings
from app.db import BillingAction, BillingActionLog, BillingCase, SessionLocal
from app.services.ticket_service import TicketService, TicketServiceError


class BillingTicketConfigError(ValueError):
    pass


@dataclass
class BatchTicketResult:
    created: int
    skipped: int
    errors: int
    duration_ms: float


def _is_case_eligible(case: BillingCase) -> bool:
    return case.status_case == 'OPEN' and (case.amount_open or 0) > 0 and not case.ticket_id


def _action_key(case: BillingCase) -> str:
    return f'billing:{case.external_id}:ticket_created'


def dry_run_case_ticket(case_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        case = db.scalar(select(BillingCase).where(BillingCase.id == case_id))
        if case is None:
            raise ValueError('Case não encontrado')

        warnings: list[str] = []
        if case.ticket_id:
            warnings.append('Case já possui ticket_id')
        if case.status_case != 'OPEN':
            warnings.append('Case não está OPEN')
        if (case.amount_open or 0) <= 0:
            warnings.append('Case sem valor em aberto')
        if not get_settings().billing_ticket_enable:
            warnings.append('BILLING_TICKET_ENABLE=false')

        return {
            'case_id': case.id,
            'eligible': _is_case_eligible(case),
            'warnings': warnings,
            'payload': {
                'id_cliente': case.id_cliente,
                'id_contrato': case.id_contrato,
                'id_filial': case.filial_id,
                'external_id': case.external_id,
                'amount_open': str(case.amount_open),
            },
            'validation_error': None,
        }


def create_ticket_for_case(adapter: IXCAdapter, case_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        case = db.scalar(select(BillingCase).where(BillingCase.id == case_id))
        if case is None:
            raise ValueError('Case não encontrado')

        if case.ticket_id:
            return {'already_created': True, 'ticket_id': case.ticket_id}

        if not _is_case_eligible(case):
            raise BillingTicketConfigError('Case não elegível para criação de ticket')

        action_key = _action_key(case)
        if db.scalar(select(BillingAction).where(BillingAction.action_key == action_key)):
            return {'already_created': True, 'ticket_id': case.ticket_id or ''}

        try:
            ticket_id = TicketService(adapter).create_ticket(case)
            case.ticket_id = ticket_id
            case.ticket_status = 'OPEN'
            case.action_state = 'TICKET_OPENED'
            case.last_action_at = datetime.utcnow()
            db.add(BillingAction(action_key=action_key, external_id=case.external_id))
            db.add(
                BillingActionLog(
                    case_id=case.id,
                    action_type='create_ticket',
                    payload_json={'ticket_id': ticket_id},
                    success=True,
                )
            )
            db.commit()
            return {'already_created': False, 'ticket_id': ticket_id}
        except TicketServiceError as exc:
            case.ticket_status = 'ERROR'
            case.action_state = 'ERROR'
            case.last_action_at = datetime.utcnow()
            db.add(BillingActionLog(case_id=case.id, action_type='create_ticket', payload_json={}, success=False, error=str(exc)))
            db.commit()
            raise BillingTicketConfigError(str(exc)) from exc


def _query_cases_for_batch(filters: dict[str, Any] | None, case_ids: list[str] | None, limit: int) -> list[BillingCase]:
    with SessionLocal() as db:
        query = select(BillingCase)
        if case_ids:
            query = query.where(BillingCase.id.in_(case_ids))
        elif filters:
            query = query.where(BillingCase.status_case == str(filters.get('status') or 'OPEN').upper())
            if filters.get('filial_id'):
                query = query.where(BillingCase.filial_id == str(filters['filial_id']))
            if filters.get('min_days') is not None:
                query = query.where(BillingCase.open_days >= int(filters['min_days']))
            if filters.get('due_from'):
                query = query.where(BillingCase.due_date >= date.fromisoformat(filters['due_from']))
            if filters.get('due_to'):
                query = query.where(BillingCase.due_date <= date.fromisoformat(filters['due_to']))
        else:
            query = query.where(BillingCase.status_case == 'OPEN')
        rows = list(db.scalars(query.order_by(BillingCase.open_days.desc()).limit(max(1, limit))))
        for row in rows:
            db.expunge(row)
        return rows


def batch_dry_run(case_ids: list[str] | None, filters: dict[str, Any] | None, limit: int) -> dict[str, Any]:
    rows = _query_cases_for_batch(filters, case_ids, limit)
    eligible = [r for r in rows if _is_case_eligible(r)]
    warnings = [] if get_settings().billing_ticket_enable else ['BILLING_TICKET_ENABLE=false']
    return {
        'count': len(eligible),
        'sample': [
            {'id': r.id, 'external_id': r.external_id, 'ticket_id': r.ticket_id, 'eligible': _is_case_eligible(r)}
            for r in eligible[:10]
        ],
        'warnings': warnings,
    }


def batch_create_tickets(adapter: IXCAdapter, case_ids: list[str] | None, filters: dict[str, Any] | None, limit: int, require_confirm: bool) -> BatchTicketResult:
    if not require_confirm:
        raise ValueError('require_confirm=true é obrigatório')

    started = perf_counter()
    rows = _query_cases_for_batch(filters, case_ids, limit)
    max_batch = max(1, min(get_settings().billing_ticket_daily_limit, get_settings().billing_ticket_batch_limit))
    eligible = [r for r in rows if _is_case_eligible(r)][:max_batch]

    created = 0
    skipped = max(0, len(rows) - len(eligible))
    errors = 0
    for case in eligible:
        try:
            result = create_ticket_for_case(adapter, case.id)
            if not result.get('already_created'):
                created += 1
        except Exception:
            errors += 1

    return BatchTicketResult(created=created, skipped=skipped, errors=errors, duration_ms=round((perf_counter() - started) * 1000, 2))


def reconcile_tickets(adapter: IXCAdapter, limit: int = 1000) -> dict[str, Any]:
    settings = get_settings()
    with SessionLocal() as db:
        rows = list(db.scalars(select(BillingCase).where(and_(BillingCase.status_case == 'OPEN', BillingCase.ticket_id.is_not(None))).limit(max(1, limit))))
        ixc_rows = adapter.list_contas_receber_by_ids([r.external_id for r in rows])
        ixc_by_id = {str(r.get('id')): r for r in ixc_rows}

        closed = 0
        would_close = 0
        errors = 0
        for case in rows:
            row = ixc_by_id.get(case.external_id)
            paid = row is None or str(row.get('valor_aberto') or '0') in {'0', '0.00'}
            if not paid:
                continue

            if not settings.billing_autoclose_enabled:
                case.action_state = 'READY_TO_CLOSE'
                case.last_action_at = datetime.utcnow()
                would_close += 1
                db.add(BillingActionLog(case_id=case.id, action_type='close_ticket', payload_json={'would_close': True}, success=True))
                continue

            try:
                case.status_case = 'RESOLVED'
                TicketService(adapter).close_ticket(case)
                case.ticket_status = 'CLOSED'
                case.action_state = 'TICKET_CLOSED'
                case.last_action_at = datetime.utcnow()
                closed += 1
                db.add(BillingActionLog(case_id=case.id, action_type='close_ticket', payload_json={'ticket_id': case.ticket_id}, success=True))
            except Exception as exc:
                errors += 1
                case.ticket_status = 'ERROR'
                case.action_state = 'ERROR'
                case.last_action_at = datetime.utcnow()
                db.add(BillingActionLog(case_id=case.id, action_type='close_ticket', payload_json={'ticket_id': case.ticket_id}, success=False, error=str(exc)))

        db.commit()
        return {'closed': closed, 'would_close': would_close, 'errors': errors}
