from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.dashboard import AgendaWeekResponse, DashboardItem, DashboardSummary
from app.services.cache import get_json as cache_get_json
from app.services.cache import set_json as cache_set_json
from app.services.adapters import get_ixc_adapter
from app.services.dashboard import agenda_week_range, build_agenda_week, build_dashboard_summary, fetch_maintenance_items, maintenances_range
from app.services.filters import get_saved_filter_definition

router = APIRouter(prefix='/dashboard', tags=['dashboard'])


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
def get_summary(
    start: str | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=31),
    filial_id: str | None = Query(default=None, pattern='^(1|2)$'),
    today: str | None = Query(default=None),
    tz: str | None = Query(default='America/Sao_Paulo'),
    filter_id: str | None = Query(default=None),
    filter_json: str | None = Query(default=None),
    adapter=Depends(get_ixc_adapter),
): 
    definition = _resolve_definition(filter_id, filter_json)
    date_start, _ = agenda_week_range(start, days)
    cache_key = f"dashboard:summary:v1:{filial_id or 'all'}:{date_start.strftime('%Y-%m-%d')}:{days}:{today or 'auto'}:{tz or 'server'}:{filter_id or '-'}:{filter_json or '-'}"
    cached = cache_get_json(cache_key)
    if cached is not None:
        return cached

    payload = build_dashboard_summary(adapter, date_start, days, definition, filial_id=filial_id, today=today, tz_name=tz)
    cache_set_json(cache_key, payload, ttl_seconds=45)
    return payload
