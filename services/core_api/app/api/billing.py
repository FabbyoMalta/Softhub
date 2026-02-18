import logging
from datetime import date
from decimal import Decimal
from time import perf_counter

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func

from app.config import get_settings
from app.db import BillingCase, SessionLocal
from app.models.billing import (
    BillingActionOut,
    BillingBatchFilters,
    BillingCasesSummaryOut,
    BillingCaseOut,
    BillingEnrichOut,
    BillingOpenResponse,
    BillingReconcileOut,
    BillingSyncOut,
    BillingTicketBatchDryRunOut,
    BillingTicketBatchIn,
    BillingTicketBatchOut,
    BillingTicketCreateOut,
    BillingTicketDryRunOut,
)
from app.services.adapters import get_ixc_adapter
from app.services.billing import build_billing_open_response, list_billing_actions
from app.services.billing_enrich import enrich_billing_cases
from app.services.billing_sync import sync_billing_cases
from app.services.billing_tickets import (
    BillingTicketConfigError,
    batch_create_tickets,
    batch_dry_run,
    create_ticket_for_case,
    dry_run_case_ticket,
    reconcile_tickets,
)
from app.utils.cache import cache_get_json, cache_set_json

router = APIRouter(prefix='/billing', tags=['billing'])
logger = logging.getLogger(__name__)


@router.get('/open', response_model=BillingOpenResponse)
def get_billing_open(response: Response, adapter=Depends(get_ixc_adapter)):
    started_at = perf_counter()
    cache_key = 'softhub:billing:open:v1'
    cached = cache_get_json(cache_key)
    if cached is not None:
        response.headers['X-Cache'] = 'HIT'
        logger.info(
            'billing.open completed',
            extra={
                'event': 'billing.open',
                'cache': 'HIT',
                'items_count': len(cached.get('items', [])),
                'elapsed_ms': round((perf_counter() - started_at) * 1000, 2),
            },
        )
        return cached

    payload = build_billing_open_response(adapter)
    cache_set_json(cache_key, payload, ttl_s=get_settings().dashboard_cache_ttl_s)
    response.headers['X-Cache'] = 'MISS'
    return payload


@router.get('/actions', response_model=list[BillingActionOut])
def get_billing_actions(limit: int = Query(default=200, ge=1, le=1000)):
    return list_billing_actions(limit)


@router.post('/sync', response_model=BillingSyncOut)
def post_billing_sync(
    min_days: int = Query(default=20, ge=0),
    due_from: date | None = Query(default=None),
    due_to: date | None = Query(default=None),
    filial_id: str | None = Query(default=None),
    adapter=Depends(get_ixc_adapter),
):
    result = sync_billing_cases(adapter=adapter, min_days=min_days, due_from=due_from, due_to=due_to, filial_id=filial_id)
    return BillingSyncOut(synced=result.synced, upserted=result.upserted, duration_ms=result.duration_ms)


@router.post('/enrich', response_model=BillingEnrichOut)
def post_billing_enrich(
    limit: int = Query(default=2000, ge=1, le=10000),
    only_missing: bool = Query(default=True),
    adapter=Depends(get_ixc_adapter),
):
    result = enrich_billing_cases(adapter=adapter, limit=limit, only_missing=only_missing)
    return BillingEnrichOut(updated=result.updated, duration_ms=result.duration_ms)


@router.post('/cases/{case_id}/ticket/dry-run', response_model=BillingTicketDryRunOut)
def post_case_ticket_dry_run(case_id: str):
    try:
        return BillingTicketDryRunOut(**dry_run_case_ticket(case_id))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post('/cases/{case_id}/ticket', response_model=BillingTicketCreateOut)
def post_case_ticket(case_id: str, adapter=Depends(get_ixc_adapter)):
    try:
        result = create_ticket_for_case(adapter, case_id)
        return BillingTicketCreateOut(already_created=bool(result.get('already_created')), ticket_id=str(result.get('ticket_id') or ''))
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except BillingTicketConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/tickets/batch/dry-run', response_model=BillingTicketBatchDryRunOut)
def post_tickets_batch_dry_run(body: BillingTicketBatchIn):
    filters = body.filters.model_dump() if body.filters else None
    result = batch_dry_run(case_ids=body.case_ids, filters=filters, limit=int(body.limit or 50))
    return BillingTicketBatchDryRunOut(**result)


@router.post('/tickets/batch', response_model=BillingTicketBatchOut)
def post_tickets_batch(body: BillingTicketBatchIn, adapter=Depends(get_ixc_adapter)):
    filters = body.filters.model_dump() if body.filters else None
    try:
        result = batch_create_tickets(
            adapter=adapter,
            case_ids=body.case_ids,
            filters=filters,
            limit=int(body.limit or 50),
            require_confirm=bool(body.require_confirm),
        )
        return BillingTicketBatchOut(
            created=result.created,
            skipped=result.skipped,
            errors=result.errors,
            duration_ms=result.duration_ms,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except BillingTicketConfigError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post('/tickets/reconcile', response_model=BillingReconcileOut)
def post_tickets_reconcile(
    limit: int = Query(default=1000, ge=1, le=5000),
    adapter=Depends(get_ixc_adapter),
):
    result = reconcile_tickets(adapter=adapter, limit=limit)
    return BillingReconcileOut(**result)


@router.get('/ticket-config/check')
def get_ticket_config_check():
    s = get_settings()
    missing = []
    if not s.billing_ticket_endpoint:
        missing.append('BILLING_TICKET_ENDPOINT')
    if not s.billing_ticket_setor_id:
        missing.append('BILLING_TICKET_SETOR_ID')
    if not s.billing_ticket_assunto_id:
        missing.append('BILLING_TICKET_ASSUNTO_ID')
    if not s.billing_ticket_close_endpoint:
        missing.append('BILLING_TICKET_CLOSE_ENDPOINT')
    return {'ok': not missing, 'missing': missing, 'autoclose_enabled': s.billing_autoclose_enabled}


@router.get('/cases', response_model=list[BillingCaseOut])
def get_billing_cases(
    status: str = Query(default='OPEN'),
    filial_id: str | None = Query(default=None),
    min_days: int | None = Query(default=None, ge=0),
    due_from: date | None = Query(default=None),
    due_to: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
):
    with SessionLocal() as db:
        query = db.query(BillingCase).filter(BillingCase.status_case == status)
        if filial_id:
            query = query.filter(BillingCase.filial_id == filial_id)
        if min_days is not None:
            query = query.filter(BillingCase.open_days >= min_days)
        if due_from:
            query = query.filter(BillingCase.due_date >= due_from)
        if due_to:
            query = query.filter(BillingCase.due_date <= due_to)
        return query.order_by(BillingCase.open_days.desc(), BillingCase.due_date.asc()).offset(offset).limit(limit).all()


@router.get('/cases/summary', response_model=BillingCasesSummaryOut)
def get_billing_cases_summary(
    status: str = Query(default='OPEN'),
    filial_id: str | None = Query(default=None),
    min_days: int | None = Query(default=None, ge=0),
    due_from: date | None = Query(default=None),
    due_to: date | None = Query(default=None),
):
    with SessionLocal() as db:
        filtered = db.query(BillingCase).filter(BillingCase.status_case == status)
        if filial_id:
            filtered = filtered.filter(BillingCase.filial_id == filial_id)
        if min_days is not None:
            filtered = filtered.filter(BillingCase.open_days >= min_days)
        if due_from:
            filtered = filtered.filter(BillingCase.due_date >= due_from)
        if due_to:
            filtered = filtered.filter(BillingCase.due_date <= due_to)

        totals = filtered.with_entities(
            func.count(BillingCase.id),
            func.coalesce(func.sum(BillingCase.amount_open), 0),
            func.min(BillingCase.due_date),
        ).one()
        by_filial_rows = filtered.with_entities(BillingCase.filial_id, func.count(BillingCase.id)).group_by(BillingCase.filial_id).all()

    by_filial = {row[0] or 'UNKNOWN': row[1] for row in by_filial_rows}
    return BillingCasesSummaryOut(total_cases=totals[0], total_amount_open=Decimal(totals[1]), oldest_due_date=totals[2], by_filial=by_filial)
