from __future__ import annotations

import json
import logging
from datetime import timedelta
from time import perf_counter

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.models.dashboard import AgendaWeekResponse, DashboardItem, DashboardSummary, InstallationsPendingResponse
from app.config import get_settings
from app.services.adapters import get_ixc_adapter
from app.services.dashboard import (
    _load_subject_ids,
    agenda_week_range,
    build_agenda_week,
    compose_dashboard_summary,
    fetch_install_period_rows,
    fetch_maint_done_rows,
    fetch_maint_done_today_rows,
    fetch_maint_backlog_rows,
    fetch_maint_opened_today_rows,
    fetch_maint_period_rows,
    fetch_maintenance_items,
    maintenances_range,
    _resolve_today,
    build_installations_pending_response,
    fetch_installations_pending_rows,
    resolve_period,
)
from app.services.filters import get_saved_filter_definition
from app.utils.cache import cache_get_json, cache_set_json, stable_json_hash
from app.utils.profiling import timer

router = APIRouter(prefix='/dashboard', tags=['dashboard'])
logger = logging.getLogger(__name__)


def _resolve_definition(filter_id: str | None, filter_json: str | None) -> dict:
    if filter_json:
        return json.loads(filter_json)
    if filter_id:
        definition = get_saved_filter_definition(filter_id)
        if definition is None:
            raise HTTPException(status_code=404, detail='filter not found')
        return definition
    return {}


@router.get('/agenda-week', response_model=AgendaWeekResponse)
def get_agenda_week(
    start: str | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=31),
    period: str | None = Query(default=None),
    filter_id: str | None = Query(default=None),
    filter_json: str | None = Query(default=None),
    filial_id: str | None = Query(default=None, pattern='^(1|2)$'),
    adapter=Depends(get_ixc_adapter),
):
    definition = _resolve_definition(filter_id, filter_json)
    start, days = resolve_period(period, start, days)
    date_start, _ = agenda_week_range(start, days)
    return build_agenda_week(adapter, date_start, days, definition, filial_id=filial_id)


@router.get('/maintenances', response_model=list[DashboardItem])
def get_maintenances(
    from_: str | None = Query(default=None, alias='from'),
    to: str | None = Query(default=None),
    tab: str = Query(default='open', pattern='^(open|scheduled|done)$'),
    filter_id: str | None = Query(default=None),
    filter_json: str | None = Query(default=None),
    adapter=Depends(get_ixc_adapter),
):
    definition = _resolve_definition(filter_id, filter_json)
    if from_ or to:
        date_start, date_end = maintenances_range(from_, to)
        return fetch_maintenance_items(adapter, definition, tab=tab, date_start=date_start, date_end=date_end)
    return fetch_maintenance_items(adapter, definition, tab=tab)


@router.get('/summary', response_model=DashboardSummary)
async def get_summary(
    start: str | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=31),
    period: str | None = Query(default=None),
    filial_id: str | None = Query(default=None, pattern='^(1|2)$'),
    today: str | None = Query(default=None),
    tz: str | None = Query(default='America/Sao_Paulo'),
    filter_id: str | None = Query(default=None),
    filter_json: str | None = Query(default=None),
    response: Response = None,
    adapter=Depends(get_ixc_adapter),
): 
    definition = _resolve_definition(filter_id, filter_json)
    today_date = _resolve_today(today, tz)
    start, days = resolve_period(period, start, days, today_override=today_date)
    date_start, _ = agenda_week_range(start, days)
    filter_hash = stable_json_hash(definition)
    cache_key = f"softhub:dash:summary:{date_start.strftime('%Y-%m-%d')}:{days}:{filial_id or 'all'}:{filter_hash}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        response.headers['X-Cache'] = 'HIT'
        return cached

    response.headers['X-Cache'] = 'MISS'

    with timer('api.dashboard.summary', logger, {'endpoint': '/dashboard/summary', 'days': days, 'filial_id': filial_id}):
        install_subject_ids, maintenance_subject_ids = _load_subject_ids()
        total_days = max(1, min(days, 31))
        date_end = date_start + timedelta(days=total_days - 1)

        t0 = perf_counter()

        t_ixc_start = perf_counter()
        install_rows = await anyio.to_thread.run_sync(lambda: fetch_install_period_rows(adapter, date_start, date_end, install_subject_ids, filial_id))
        tempo_ixc_installs_period = perf_counter() - t_ixc_start

        t_ixc_start = perf_counter()
        install_overdue_rows = await anyio.to_thread.run_sync(lambda: fetch_installations_pending_rows(adapter, today_date, install_subject_ids, filial_id))
        tempo_ixc_installs_overdue = perf_counter() - t_ixc_start

        t_ixc_start = perf_counter()
        maint_period_rows = await anyio.to_thread.run_sync(lambda: fetch_maint_period_rows(adapter, date_start, date_end, maintenance_subject_ids, filial_id))
        tempo_ixc_maint_period = perf_counter() - t_ixc_start

        t_ixc_start = perf_counter()
        maint_done_rows = await anyio.to_thread.run_sync(lambda: fetch_maint_done_rows(adapter, date_start, date_end, maintenance_subject_ids, filial_id))
        maint_backlog_rows = await anyio.to_thread.run_sync(lambda: fetch_maint_backlog_rows(adapter, maintenance_subject_ids, filial_id))
        maint_opened_today_rows = await anyio.to_thread.run_sync(lambda: fetch_maint_opened_today_rows(adapter, today_date, maintenance_subject_ids, filial_id))
        maint_done_today_rows = await anyio.to_thread.run_sync(lambda: fetch_maint_done_today_rows(adapter, today_date, maintenance_subject_ids, filial_id))
        tempo_ixc_maint_aux = perf_counter() - t_ixc_start

        t_process_start = perf_counter()
        payload = compose_dashboard_summary(
            date_start,
            total_days,
            today_date,
            definition,
            install_rows,
            maint_period_rows,
            maint_done_rows,
            maint_backlog_rows,
            maint_opened_today_rows,
            maint_done_today_rows,
            install_overdue_rows,
        )
        tempo_processamento = perf_counter() - t_process_start
        tempo_total = perf_counter() - t0

        logger.info(
            'dashboard.summary perf tempo_total=%.4fs tempo_ixc_installs_period=%.4fs tempo_ixc_installs_overdue=%.4fs tempo_ixc_maint_period=%.4fs tempo_ixc_maint_aux=%.4fs tempo_processamento=%.4fs',
            tempo_total,
            tempo_ixc_installs_period,
            tempo_ixc_installs_overdue,
            tempo_ixc_maint_period,
            tempo_ixc_maint_aux,
            tempo_processamento,
        )

    cache_set_json(cache_key, payload, ttl_s=get_settings().dashboard_cache_ttl_s)
    return payload



@router.get('/installations-pending', response_model=InstallationsPendingResponse)
def get_installations_pending(
    start: str | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=31),
    filter_id: str | None = Query(default=None),
    filter_json: str | None = Query(default=None),
    filial_id: str | None = Query(default=None, pattern='^(1|2)$'),
    limit: int = Query(default=200, ge=1, le=1000),
    today: str | None = Query(default=None),
    tz: str | None = Query(default='America/Sao_Paulo'),
    adapter=Depends(get_ixc_adapter),
):
    # start/days kept for compatibility; pending is always < today
    _resolve_definition(filter_id, filter_json)
    today_date = _resolve_today(today, tz)
    return build_installations_pending_response(adapter, today_date=today_date, limit=limit, filial_id=filial_id)
