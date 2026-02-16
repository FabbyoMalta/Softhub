from __future__ import annotations

import json
import logging
from datetime import timedelta

import anyio
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from app.models.dashboard import AgendaWeekResponse, DashboardItem, DashboardSummary
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
    fetch_maint_open_rows,
    fetch_maint_opened_today_rows,
    fetch_maint_period_rows,
    fetch_install_done_today_rows,
    fetch_maintenance_items,
    fetch_install_scheduled_today_rows,
    maintenances_range,
    _resolve_today,
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
    filter_id: str | None = Query(default=None),
    filter_json: str | None = Query(default=None),
    filial_id: str | None = Query(default=None, pattern='^(1|2)$'),
    adapter=Depends(get_ixc_adapter),
):
    definition = _resolve_definition(filter_id, filter_json)
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
    filial_id: str | None = Query(default=None, pattern='^(1|2)$'),
    today: str | None = Query(default=None),
    tz: str | None = Query(default='America/Sao_Paulo'),
    filter_id: str | None = Query(default=None),
    filter_json: str | None = Query(default=None),
    response: Response = None,
    adapter=Depends(get_ixc_adapter),
): 
    definition = _resolve_definition(filter_id, filter_json)
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
        today_date = _resolve_today(today, tz)

        results: dict[str, list[dict]] = {}

        async def run(name: str, fn):
            data = await anyio.to_thread.run_sync(fn)
            results[name] = data

        async with anyio.create_task_group() as tg:
            tg.start_soon(run, 'install_rows', lambda: fetch_install_period_rows(adapter, date_start, date_end, install_subject_ids, filial_id))
            tg.start_soon(run, 'maint_period_rows', lambda: fetch_maint_period_rows(adapter, date_start, date_end, maintenance_subject_ids, filial_id))
            tg.start_soon(run, 'maint_open_rows', lambda: fetch_maint_open_rows(adapter, date_start, date_end, maintenance_subject_ids, filial_id))
            tg.start_soon(run, 'maint_done_rows', lambda: fetch_maint_done_rows(adapter, date_start, date_end, maintenance_subject_ids, filial_id))
            tg.start_soon(run, 'maint_backlog_rows', lambda: fetch_maint_backlog_rows(adapter, maintenance_subject_ids, filial_id))
            tg.start_soon(run, 'maint_opened_today_rows', lambda: fetch_maint_opened_today_rows(adapter, today_date, maintenance_subject_ids, filial_id))
            tg.start_soon(run, 'install_scheduled_today_rows', lambda: fetch_install_scheduled_today_rows(adapter, today_date, install_subject_ids, filial_id))
            tg.start_soon(run, 'install_done_today_rows', lambda: fetch_install_done_today_rows(adapter, today_date, install_subject_ids, filial_id))
            tg.start_soon(run, 'maint_done_today_rows', lambda: fetch_maint_done_today_rows(adapter, today_date, maintenance_subject_ids, filial_id))

        payload = compose_dashboard_summary(
            date_start,
            total_days,
            today_date,
            definition,
            results.get('install_rows', []),
            results.get('maint_period_rows', []),
            results.get('maint_open_rows', []),
            results.get('maint_done_rows', []),
            results.get('maint_backlog_rows', []),
            results.get('maint_opened_today_rows', []),
            results.get('install_scheduled_today_rows', []),
            results.get('install_done_today_rows', []),
            results.get('maint_done_today_rows', []),
        )

    cache_set_json(cache_key, payload, ttl_s=get_settings().dashboard_cache_ttl_s)
    return payload
