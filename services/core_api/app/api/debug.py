from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query

from app.config import get_settings
from app.utils.profiling import last_events

router = APIRouter(prefix='/debug', tags=['debug'])


@router.get('/perf/last')
def get_perf_last(limit: int = Query(default=100, ge=1, le=500)):
    if not get_settings().softhub_profile:
        raise HTTPException(status_code=404, detail='profiling disabled')
    return {'events': last_events(limit), 'count': min(limit, len(last_events(limit)))}
