from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from app.adapters.ixc_adapter import IXCAdapter


def parse_date_or_default(raw: str | None, default: date) -> date:
    if not raw:
        return default
    return datetime.strptime(raw, '%Y-%m-%d').date()


def parse_date_range_from_definition(definition_json: dict[str, Any] | None) -> tuple[date, date] | None:
    if not definition_json:
        return None
    date_range = definition_json.get('date_range')
    if not isinstance(date_range, dict):
        return None
    start_raw = date_range.get('start')
    end_raw = date_range.get('end')
    if not (isinstance(start_raw, str) and isinstance(end_raw, str)):
        return None
    start = datetime.strptime(start_raw, '%Y-%m-%d').date()
    end = datetime.strptime(end_raw, '%Y-%m-%d').date()
    return (start, end) if start <= end else (end, start)


def agenda_week_range(start_raw: str | None, days: int) -> tuple[date, date]:
    start = parse_date_or_default(start_raw, date.today())
    total_days = max(1, min(days, 31))
    end = start + timedelta(days=total_days - 1)
    return start, end


def maintenances_range(from_raw: str | None, to_raw: str | None) -> tuple[date, date]:
    default_start = date.today() - timedelta(days=7)
    default_end = date.today() + timedelta(days=7)
    start = parse_date_or_default(from_raw, default_start)
    end = parse_date_or_default(to_raw, default_end)
    return (start, end) if start <= end else (end, start)


def normalize_os_item(item: dict[str, Any]) -> dict[str, Any]:
    os_type = str(item.get('tipo') or item.get('type') or 'manutencao').lower()
    if os_type not in {'instalacao', 'manutencao'}:
        os_type = 'manutencao'

    return {
        'id': str(item.get('id') or item.get('external_id') or ''),
        'date': item.get('data_agendada') or item.get('date') or '',
        'time': item.get('hora_agendada') or item.get('time'),
        'type': os_type,
        'status': item.get('status'),
        'customer_id': str(item.get('id_cliente') or item.get('customer_id') or ''),
        'customer_name': item.get('cliente') or item.get('customer_name'),
        'city': item.get('cidade') or item.get('city'),
        'neighborhood': item.get('bairro') or item.get('neighborhood'),
        'address': item.get('endereco') or item.get('address'),
        'source': 'ixc',
    }


def list_service_orders_by_grid(adapter: IXCAdapter, grid_filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = adapter.list_service_orders(grid_filters)
    return [normalize_os_item(row) for row in rows]
