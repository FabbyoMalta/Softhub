from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status

from app.models.dashboard import SavedFilterIn, SavedFilterOut
from app.services.filters import (
    create_saved_filter,
    delete_saved_filter,
    get_saved_filter,
    list_saved_filters,
    update_saved_filter,
)

router = APIRouter(tags=['filters'])


@router.get('/filters', response_model=list[SavedFilterOut])
def get_filters(scope: str = Query(...)):
    return list_saved_filters(scope)


@router.post('/filters', response_model=SavedFilterOut, status_code=status.HTTP_201_CREATED)
def post_filters(payload: SavedFilterIn):
    return create_saved_filter(payload.name, payload.scope, payload.definition_json)


@router.get('/filters/{filter_id}', response_model=SavedFilterOut)
def get_filter(filter_id: str):
    row = get_saved_filter(filter_id)
    if row is None:
        raise HTTPException(status_code=404, detail='filter not found')
    return row


@router.put('/filters/{filter_id}', response_model=SavedFilterOut)
def put_filter(filter_id: str, payload: SavedFilterIn):
    row = update_saved_filter(filter_id, payload.name, payload.scope, payload.definition_json)
    if row is None:
        raise HTTPException(status_code=404, detail='filter not found')
    return row


@router.delete('/filters/{filter_id}', status_code=status.HTTP_204_NO_CONTENT)
def remove_filter(filter_id: str):
    removed = delete_saved_filter(filter_id)
    if not removed:
        raise HTTPException(status_code=404, detail='filter not found')
