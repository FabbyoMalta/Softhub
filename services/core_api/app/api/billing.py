from fastapi import APIRouter, Depends, Query, Response

from app.config import get_settings
from app.models.billing import BillingActionOut, BillingOpenResponse
from app.services.adapters import get_ixc_adapter
from app.services.billing import build_billing_open_response, list_billing_actions
from app.utils.cache import cache_get_json, cache_set_json

router = APIRouter(prefix='/billing', tags=['billing'])


@router.get('/open', response_model=BillingOpenResponse)
def get_billing_open(response: Response, adapter=Depends(get_ixc_adapter)):
    cache_key = 'softhub:billing:open:v1'
    cached = cache_get_json(cache_key)
    if cached is not None:
        response.headers['X-Cache'] = 'HIT'
        return cached

    payload = build_billing_open_response(adapter)
    cache_set_json(cache_key, payload, ttl_s=get_settings().dashboard_cache_ttl_s)
    response.headers['X-Cache'] = 'MISS'
    return payload


@router.get('/actions', response_model=list[BillingActionOut])
def get_billing_actions(limit: int = Query(default=200, ge=1, le=1000)):
    return list_billing_actions(limit)
