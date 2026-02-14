from __future__ import annotations

from datetime import date
from typing import Any

TB_OS_DATA_AGENDA = 'su_oss_chamado.data_agenda'
TB_OS_STATUS = 'su_oss_chamado.status'
TB_OS_ID_ASSUNTO = 'su_oss_chamado.id_assunto'
TB_OS_ID_CLIENTE = 'su_oss_chamado.id_cliente'


def _f(tb: str, op: str, p: Any) -> dict[str, str]:
    return {'TB': tb, 'OP': op, 'P': str(p)}


def build_os_grid(
    date_start: date,
    date_end: date,
    statuses: list[str] | None,
    assunto_ids: list[str] | None,
) -> list[dict[str, str]]:
    grid: list[dict[str, str]] = [
        _f(TB_OS_DATA_AGENDA, '>=', date_start.strftime('%Y-%m-%d 00:00:00')),
        _f(TB_OS_DATA_AGENDA, '<=', date_end.strftime('%Y-%m-%d 23:59:59')),
    ]

    if statuses:
        if len(statuses) == 1:
            grid.append(_f(TB_OS_STATUS, '=', statuses[0]))
        else:
            grid.append(_f(TB_OS_STATUS, 'IN', ','.join(statuses)))

    if assunto_ids:
        if len(assunto_ids) == 1:
            grid.append(_f(TB_OS_ID_ASSUNTO, '=', assunto_ids[0]))
        else:
            grid.append(_f(TB_OS_ID_ASSUNTO, 'IN', ','.join(assunto_ids)))

    return grid


def expand_os_query_grids(
    date_start: date,
    date_end: date,
    statuses: list[str] | None,
    assunto_ids: list[str] | None,
    use_in: bool,
) -> list[list[dict[str, str]]]:
    if use_in:
        return [build_os_grid(date_start, date_end, statuses, assunto_ids)]

    status_list = statuses or [None]
    assunto_list = assunto_ids or [None]
    grids: list[list[dict[str, str]]] = []
    for status in status_list:
        for assunto in assunto_list:
            grids.append(
                build_os_grid(
                    date_start,
                    date_end,
                    [status] if status else None,
                    [assunto] if assunto else None,
                )
            )
    return grids
