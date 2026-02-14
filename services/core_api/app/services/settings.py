from __future__ import annotations

from sqlalchemy import select

from app.db import SessionLocal, Setting

SETTINGS_KEY = 'app_settings'
DEFAULT_SETTINGS = {
    'default_filters': {'agenda': None, 'manutencoes': None},
    'subject_groups': {'instalacao': ['1'], 'manutencao': ['17', '34', '31'], 'outros': []},
}


def get_settings_payload() -> dict:
    with SessionLocal() as session:
        row = session.scalar(select(Setting).where(Setting.key == SETTINGS_KEY))
        if row is None:
            row = Setting(key=SETTINGS_KEY, value_json=DEFAULT_SETTINGS)
            session.add(row)
            session.commit()
            session.refresh(row)
        return row.value_json


def update_settings_payload(payload: dict) -> dict:
    with SessionLocal() as session:
        row = session.scalar(select(Setting).where(Setting.key == SETTINGS_KEY))
        if row is None:
            row = Setting(key=SETTINGS_KEY, value_json=payload)
            session.add(row)
        else:
            row.value_json = payload
        session.commit()
        session.refresh(row)
        return row.value_json
