from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from time import perf_counter
from typing import Any

from sqlalchemy import and_, select

from app.adapters.ixc_adapter import IXCAdapter
from app.config import get_settings
from app.db import BillingActionLog, BillingCase, SessionLocal


class BillingTicketConfigError(ValueError):
    pass


@dataclass
class BatchTicketResult:
    created: int
    skipped: int
    errors: int
    duration_ms: float


def _build_ticket_message(case: BillingCase) -> str:
    settings = get_settings()
    template = settings.billing_ticket_mensagem_template
    contract = case.contract_json or {}
    return template.format(
        id_cliente=case.id_cliente or '-',
        id_contrato=case.id_contrato or '-',
        external_id=case.external_id or '-',
        due_date=case.due_date.isoformat() if case.due_date else '-',
        open_days=case.open_days,
        amount_open=str(case.amount_open or Decimal('0')),
        filial_id=case.filial_id or '-',
        plano_nome=contract.get('plano_nome') or '-',
    )


def _require_ticket_envs() -> None:
    s = get_settings()
    missing = []
    if not s.billing_ticket_endpoint:
        missing.append('BILLING_TICKET_ENDPOINT')
    if not s.billing_ticket_setor_id:
        missing.append('BILLING_TICKET_SETOR_ID')
    if not s.billing_ticket_assunto_id:
        missing.append('BILLING_TICKET_ASSUNTO_ID')
    if missing:
        raise BillingTicketConfigError(f'Variáveis obrigatórias ausentes: {", ".join(missing)}')


def _ticket_payload(case: BillingCase) -> dict[str, Any]:
    _require_ticket_envs()
    s = get_settings()
    return {
        'id_cliente': case.id_cliente,
        'id_contrato': case.id_contrato,
        'external_id': case.external_id,
        'due_date': case.due_date.isoformat() if case.due_date else None,
        'open_days': case.open_days,
        'amount_open': str(case.amount_open),
        'filial_id': case.filial_id,
        'setor_id': s.billing_ticket_setor_id,
        'assunto_id': s.billing_ticket_assunto_id,
        'mensagem': _build_ticket_message(case),
    }


def _is_case_eligible(case: BillingCase) -> bool:
    return case.status_case == 'OPEN' and case.open_days >= 20 and not case.ticket_id


def dry_run_case_ticket(case_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        case = db.scalar(select(BillingCase).where(BillingCase.id == case_id))
        if case is None:
            raise ValueError('Case não encontrado')

        warnings: list[str] = []
        if case.ticket_id:
            warnings.append('Case já possui ticket_id')
        if case.open_days < 20:
            warnings.append('Case com open_days < 20')
        if case.status_case != 'OPEN':
            warnings.append('Case não está OPEN')

        payload = None
        validation_error = None
        try:
            payload = _ticket_payload(case)
        except BillingTicketConfigError as exc:
            validation_error = str(exc)

        return {
            'case_id': case.id,
            'eligible': _is_case_eligible(case),
            'warnings': warnings,
            'payload': payload,
            'validation_error': validation_error,
        }


def create_ticket_for_case(adapter: IXCAdapter, case_id: str) -> dict[str, Any]:
    with SessionLocal() as db:
        case = db.scalar(select(BillingCase).where(BillingCase.id == case_id))
        if case is None:
            raise ValueError('Case não encontrado')

        if case.ticket_id:
            return {'already_created': True, 'ticket_id': case.ticket_id}

        payload = _ticket_payload(case)
        try:
            result = adapter.create_billing_ticket(payload)
            ticket_id = str(result.get('ticket_id') or '')
            if not ticket_id:
                raise ValueError('IXC não retornou ticket_id')

            case.ticket_id = ticket_id
            case.ticket_status = 'OPEN'
            case.action_state = 'TICKET_OPENED'
            case.last_action_at = datetime.utcnow()

            db.add(
                BillingActionLog(
                    case_id=case.id,
                    action_type='create_ticket',
                    payload_json={'request': payload, 'response': result},
                    success=True,
                )
            )
            db.commit()
            return {'already_created': False, 'ticket_id': ticket_id}
        except Exception as exc:
            case.ticket_status = 'ERROR'
            case.action_state = 'ERROR'
            case.last_action_at = datetime.utcnow()
            db.add(
                BillingActionLog(
                    case_id=case.id,
                    action_type='create_ticket',
                    payload_json={'request': payload},
                    success=False,
                    error=str(exc),
                )
            )
            db.commit()
            raise


def _query_cases_for_batch(filters: dict[str, Any] | None, case_ids: list[str] | None, limit: int) -> list[BillingCase]:
    with SessionLocal() as db:
        query = select(BillingCase)
        if case_ids:
            query = query.where(BillingCase.id.in_(case_ids))
        elif filters:
            query = query.where(BillingCase.status_case == str(filters.get('status') or 'OPEN'))
            filial_id = filters.get('filial_id')
            if filial_id:
                query = query.where(BillingCase.filial_id == str(filial_id))
            min_days = filters.get('min_days')
            if min_days is not None:
                query = query.where(BillingCase.open_days >= int(min_days))
            due_from = filters.get('due_from')
            if due_from:
                query = query.where(BillingCase.due_date >= date.fromisoformat(due_from))
            due_to = filters.get('due_to')
            if due_to:
                query = query.where(BillingCase.due_date <= date.fromisoformat(due_to))
        else:
            query = query.where(BillingCase.status_case == 'OPEN')

        rows = list(db.scalars(query.order_by(BillingCase.open_days.desc()).limit(max(1, limit))))
        for row in rows:
            db.expunge(row)
        return rows


def batch_dry_run(case_ids: list[str] | None, filters: dict[str, Any] | None, limit: int) -> dict[str, Any]:
    rows = _query_cases_for_batch(filters, case_ids, limit)
    eligible = [r for r in rows if _is_case_eligible(r)]
    warnings: list[str] = []
    try:
        _require_ticket_envs()
    except BillingTicketConfigError as exc:
        warnings.append(str(exc))

    sample = [
        {
            'id': r.id,
            'external_id': r.external_id,
            'open_days': r.open_days,
            'status_case': r.status_case,
            'ticket_id': r.ticket_id,
            'eligible': _is_case_eligible(r),
        }
        for r in eligible[:10]
    ]
    return {'count': len(eligible), 'sample': sample, 'warnings': warnings}


def batch_create_tickets(
    adapter: IXCAdapter,
    case_ids: list[str] | None,
    filters: dict[str, Any] | None,
    limit: int,
    require_confirm: bool,
) -> BatchTicketResult:
    if not require_confirm:
        raise ValueError('require_confirm=true é obrigatório')

    started = perf_counter()
    rows = _query_cases_for_batch(filters, case_ids, limit)
    max_batch = max(1, get_settings().billing_ticket_batch_limit)
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

    return BatchTicketResult(
        created=created,
        skipped=skipped,
        errors=errors,
        duration_ms=round((perf_counter() - started) * 1000, 2),
    )


def reconcile_tickets(adapter: IXCAdapter, limit: int = 1000) -> dict[str, Any]:
    settings = get_settings()
    with SessionLocal() as db:
        rows = list(
            db.scalars(
                select(BillingCase)
                .where(and_(BillingCase.status_case == 'OPEN', BillingCase.ticket_id.is_not(None)))
                .order_by(BillingCase.last_seen_at.desc())
                .limit(max(1, limit))
            )
        )

        external_ids = [r.external_id for r in rows]
        ixc_rows = adapter.list_contas_receber_by_ids(external_ids)
        ixc_by_id = {str(r.get('id')): r for r in ixc_rows}

        closed = 0
        would_close = 0
        errors = 0
        max_close = max(1, settings.billing_autoclose_limit)
        closed_now = 0

        for case in rows:
            row = ixc_by_id.get(case.external_id)
            should_close = row is None or str(row.get('valor_aberto') or '0') in {'0', '0.00'}
            if not should_close:
                continue

            if not settings.billing_autoclose_enabled:
                case.action_state = 'READY_TO_CLOSE'
                case.last_action_at = datetime.utcnow()
                db.add(
                    BillingActionLog(
                        case_id=case.id,
                        action_type='close_ticket',
                        payload_json={'would_close': True, 'ticket_id': case.ticket_id},
                        success=True,
                    )
                )
                would_close += 1
                continue

            if closed_now >= max_close:
                continue

            try:
                adapter.close_billing_ticket(case.ticket_id or '', {'external_id': case.external_id})
                case.status_case = 'RESOLVED'
                case.ticket_status = 'CLOSED'
                case.action_state = 'TICKET_CLOSED'
                case.last_action_at = datetime.utcnow()
                db.add(
                    BillingActionLog(
                        case_id=case.id,
                        action_type='close_ticket',
                        payload_json={'ticket_id': case.ticket_id},
                        success=True,
                    )
                )
                closed += 1
                closed_now += 1
            except Exception as exc:
                case.ticket_status = 'ERROR'
                case.action_state = 'ERROR'
                case.last_action_at = datetime.utcnow()
                db.add(
                    BillingActionLog(
                        case_id=case.id,
                        action_type='close_ticket',
                        payload_json={'ticket_id': case.ticket_id},
                        success=False,
                        error=str(exc),
                    )
                )
                errors += 1

        db.commit()
        return {'closed': closed, 'would_close': would_close, 'errors': errors}
