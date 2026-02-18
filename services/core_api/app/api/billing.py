import logging
from datetime import date
from decimal import Decimal
from time import perf_counter

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func

from app.config import get_settings
from app.db import BillingCase, SessionLocal
from app.models.billing import BillingActionOut, BillingCasesSummaryOut, BillingCaseOut, BillingOpenResponse, BillingSyncOut
from app.services.adapters import get_ixc_adapter
from app.services.billing import build_billing_open_response, list_billing_actions
from app.services.billing_sync import sync_billing_cases
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
    logger.info(
        'billing.open completed',
        extra={
            'event': 'billing.open',
            'cache': 'MISS',
            'items_count': len(payload.get('items', [])),
            'elapsed_ms': round((perf_counter() - started_at) * 1000, 2),
        },
    )
    return payload


@router.get('/actions', response_model=list[BillingActionOut])
def get_billing_actions(limit: int = Query(default=200, ge=1, le=1000)):
    started_at = perf_counter()
    actions = list_billing_actions(limit)
    logger.info(
        'billing.actions completed',
        extra={
            'event': 'billing.actions',
            'items_count': len(actions),
            'elapsed_ms': round((perf_counter() - started_at) * 1000, 2),
            'limit': limit,
        },
    )
    return actions




@router.post('/sync', response_model=BillingSyncOut)
def post_billing_sync(
    min_days: int = Query(default=20, ge=0),
    due_from: date | None = Query(default=None),
    due_to: date | None = Query(default=None),
    filial_id: str | None = Query(default=None),
    adapter=Depends(get_ixc_adapter),
):
    result = sync_billing_cases(
        adapter=adapter,
        min_days=min_days,
        due_from=due_from,
        due_to=due_to,
        filial_id=filial_id,
    )
    return BillingSyncOut(synced=result.synced, upserted=result.upserted, duration_ms=result.duration_ms)

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

        items = (
            query.order_by(BillingCase.open_days.desc(), BillingCase.due_date.asc())
            .offset(offset)
            .limit(limit)
            .all()
        )

    return items


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

        by_filial_rows = (
            filtered.with_entities(BillingCase.filial_id, func.count(BillingCase.id))
            .group_by(BillingCase.filial_id)
            .all()
        )

    by_filial = {row[0] or 'UNKNOWN': row[1] for row in by_filial_rows}

    return BillingCasesSummaryOut(
        total_cases=totals[0],
        total_amount_open=Decimal(totals[1]),
        oldest_due_date=totals[2],
        by_filial=by_filial,
    )
