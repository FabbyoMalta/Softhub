from __future__ import annotations

import logging
from datetime import date
from typing import Any

logger = logging.getLogger(__name__)

SUPPORTED_OPS = {'=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN'}

TB_OS_DATA_AGENDADA = 'su_oss_chamado.data_agendada'  # TODO confirmar
TB_OS_TIPO = 'su_oss_chamado.tipo'  # TODO confirmar
TB_OS_STATUS = 'su_oss_chamado.status'  # TODO confirmar
TB_OS_ASSUNTO = 'su_oss_chamado.assunto'  # TODO confirmar
TB_OS_CIDADE = 'su_oss_chamado.cidade'  # TODO confirmar


def _filter(tb: str, op: str, param: Any) -> dict[str, str]:
    if op not in SUPPORTED_OPS:
        raise ValueError(f'Unsupported operator: {op}')
    return {'TB': tb, 'OP': op, 'P': str(param)}


def build_type_filter(types: list[str] | None) -> list[dict[str, str]]:
    if not TB_OS_TIPO:
        logger.warning('TB_OS_TIPO not defined; skipping types filter')
        return []
    if not types:
        return []
    return [_filter(TB_OS_TIPO, '=', t.strip().lower()) for t in types if isinstance(t, str) and t.strip()]


def build_status_filter(status: list[str] | None) -> list[dict[str, str]]:
    if not TB_OS_STATUS:
        logger.warning('TB_OS_STATUS not defined; skipping status filter')
        return []
    if not status:
        return []
    return [_filter(TB_OS_STATUS, '=', s.strip().lower()) for s in status if isinstance(s, str) and s.strip()]


def build_date_filter(date_range: tuple[date, date] | None) -> list[dict[str, str]]:
    if not TB_OS_DATA_AGENDADA:
        logger.warning('TB_OS_DATA_AGENDADA not defined; skipping date filter')
        return []
    if not date_range:
        return []
    start, end = date_range
    return [
        _filter(TB_OS_DATA_AGENDADA, '>=', start.strftime('%Y-%m-%d')),
        _filter(TB_OS_DATA_AGENDADA, '<=', end.strftime('%Y-%m-%d')),
    ]


def build_text_filter(field: str, value: str | None) -> list[dict[str, str]]:
    raw = (value or '').strip()
    if not raw:
        return []

    tb_map = {
        'city_contains': TB_OS_CIDADE,
        'assunto_contains': TB_OS_ASSUNTO,
    }
    tb = tb_map.get(field)
    if not tb:
        logger.warning('TB mapping missing for text field=%s; skipping filter', field)
        return []
    return [_filter(tb, 'LIKE', f'%{raw}%')]


def build_os_grid(
    scope: str,
    definition_json: dict[str, Any] | None,
    date_range: tuple[date, date] | None,
) -> list[dict[str, str]]:
    definition = definition_json or {}

    filters: list[dict[str, str]] = []
    filters.extend(build_date_filter(date_range))
    filters.extend(build_type_filter(definition.get('types')))
    filters.extend(build_status_filter(definition.get('status') or definition.get('statuses')))
    filters.extend(build_text_filter('city_contains', definition.get('city_contains')))
    filters.extend(build_text_filter('assunto_contains', definition.get('assunto_contains')))

    if scope == 'maintenances' and not (definition.get('types') or []):
        filters.extend(build_type_filter(['manutencao']))

    supported = {'types', 'status', 'statuses', 'date_range', 'city_contains', 'assunto_contains'}
    for key in definition:
        if key not in supported:
            logger.warning('Ignoring unsupported dashboard filter field key=%s scope=%s', key, scope)

    return filters
