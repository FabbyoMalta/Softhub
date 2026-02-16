from __future__ import annotations

from fastapi import APIRouter

from app.models.dashboard import AppSettings
from app.services.settings import get_settings_payload, update_settings_payload

router = APIRouter(tags=['settings'])


@router.get('/settings', response_model=AppSettings)
def get_settings():
    return get_settings_payload()


@router.put('/settings', response_model=AppSettings)
def put_settings(payload: AppSettings):
    return update_settings_payload(payload.model_dump())
