from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, Query

from app.models.dashboard import DashboardItem
from app.services.adapters import get_ixc_adapter
from app.services.dashboard import (
    agenda_week_range,
    list_service_orders_by_grid,
    maintenances_range,
    parse_date_range_from_definition,
)
from app.services.filters import get_saved_filter_definition
from app.services.ixc_grid_builder import build_os_grid

router = APIRouter(prefix='/dashboard', tags=['dashboard'])


def _resolve_definition(filter_id: str | None, filter_json: str | None) -> dict | None:
    if filter_json:
        return json.loads(filter_json)
    if filter_id:
        definition = get_saved_filter_definition(filter_id)
        if definition is None:
            raise HTTPException(status_code=404, detail='filter not found')
        return definition
    return None


@router.get('/agenda-week', response_model=list[DashboardItem])
def get_agenda_week(
    start: str | None = Query(default=None),
    days: int = Query(default=7, ge=1, le=31),
    filter_id: str | None = Query(default=None),
    filter_json: str | None = Query(default=None),
    adapter=Depends(get_ixc_adapter),
):
    definition = _resolve_definition(filter_id, filter_json)
    start_date, end_date = agenda_week_range(start, days)
    definition_range = parse_date_range_from_definition(definition)
    date_range = definition_range or (start_date, end_date)
    grid_filters = build_os_grid('agenda_week', definition or {}, date_range)
    return list_service_orders_by_grid(adapter, grid_filters)


@router.get('/maintenances', response_model=list[DashboardItem])
def get_maintenances(
    from_: str | None = Query(default=None, alias='from'),
    to: str | None = Query(default=None),
    filter_id: str | None = Query(default=None),
    filter_json: str | None = Query(default=None),
    adapter=Depends(get_ixc_adapter),
):
    definition = _resolve_definition(filter_id, filter_json)
    start_date, end_date = maintenances_range(from_, to)
    definition_range = parse_date_range_from_definition(definition)
    date_range = definition_range or (start_date, end_date)
    grid_filters = build_os_grid('maintenances', definition or {}, date_range)
    return list_service_orders_by_grid(adapter, grid_filters)
