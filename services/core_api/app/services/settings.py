from __future__ import annotations

from copy import deepcopy

from sqlalchemy import select

from app.db import SessionLocal, Setting

SETTINGS_KEY = 'app_settings'
DEFAULT_SETTINGS = {
    'default_filters': {'agenda': None, 'manutencoes': None},
    'installation_subject_ids': ['1', '15'],
    'maintenance_subject_ids': ['17', '34', '31'],
    'subject_groups': {'instalacao': ['1'], 'manutencao': ['17', '34', '31'], 'outros': []},
    'agenda_capacity': {
        '1': {'mon': 5, 'tue': 5, 'wed': 5, 'thu': 5, 'fri': 5, 'sat': 0, 'sun': 0},
        '2': {'mon': 4, 'tue': 4, 'wed': 4, 'thu': 4, 'fri': 4, 'sat': 0, 'sun': 0},
    },
    'filiais': {'1': 'Grande Vitória', '2': 'João Neiva'},
}


def _merge_defaults(payload: dict | None) -> dict:
    merged = deepcopy(DEFAULT_SETTINGS)
    incoming = payload or {}

    if isinstance(incoming.get('default_filters'), dict):
        merged['default_filters'].update(incoming['default_filters'])

    if isinstance(incoming.get('subject_groups'), dict):
        for key in ('instalacao', 'manutencao', 'outros'):
            value = incoming['subject_groups'].get(key)
            if isinstance(value, list):
                merged['subject_groups'][key] = [str(x) for x in value]

    installation_ids = incoming.get('installation_subject_ids')
    if isinstance(installation_ids, list):
        merged['installation_subject_ids'] = [str(x) for x in installation_ids]

    maintenance_ids = incoming.get('maintenance_subject_ids')
    if isinstance(maintenance_ids, list):
        merged['maintenance_subject_ids'] = [str(x) for x in maintenance_ids]

    if isinstance(incoming.get('filiais'), dict):
        for key in ('1', '2'):
            value = incoming['filiais'].get(key)
            if isinstance(value, str) and value.strip():
                merged['filiais'][key] = value.strip()

    if isinstance(incoming.get('agenda_capacity'), dict):
        for filial_id in ('1', '2'):
            filial_capacity = incoming['agenda_capacity'].get(filial_id)
            if not isinstance(filial_capacity, dict):
                continue
            for weekday in ('mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun'):
                value = filial_capacity.get(weekday)
                if value is None:
                    continue
                try:
                    merged['agenda_capacity'][filial_id][weekday] = max(0, int(value))
                except (TypeError, ValueError):
                    continue

    return merged


def get_settings_payload() -> dict:
    with SessionLocal() as session:
        row = session.scalar(select(Setting).where(Setting.key == SETTINGS_KEY))
        if row is None:
            row = Setting(key=SETTINGS_KEY, value_json=deepcopy(DEFAULT_SETTINGS))
            session.add(row)
            session.commit()
            session.refresh(row)
            return row.value_json

        merged = _merge_defaults(row.value_json)
        if merged != row.value_json:
            row.value_json = merged
            session.commit()
            session.refresh(row)
        return row.value_json


def update_settings_payload(payload: dict) -> dict:
    normalized = _merge_defaults(payload)
    with SessionLocal() as session:
        row = session.scalar(select(Setting).where(Setting.key == SETTINGS_KEY))
        if row is None:
            row = Setting(key=SETTINGS_KEY, value_json=normalized)
            session.add(row)
        else:
            row.value_json = normalized
        session.commit()
        session.refresh(row)
        return row.value_json
