from __future__ import annotations

from datetime import date
from typing import Any

SUPPORTED_OPS = {'=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN'}
# NOTE: operador IN pode não ser suportado em todos os ambientes IXC.

TB_OS_DATA_AGENDADA = 'su_oss_chamado.data_agendada'  # TODO confirmar
TB_OS_TIPO = 'su_oss_chamado.tipo'  # TODO confirmar
TB_TICKET_STATUS = 'su_ticket.status'  # TODO confirmar


def _filter(tb: str, op: str, param: Any) -> dict[str, str]:
    if op not in SUPPORTED_OPS:
        raise ValueError(f'Unsupported operator: {op}')
    return {'TB': tb, 'OP': op, 'P': str(param)}


def build_filters_contrato_by_id(id_contrato: str | int) -> list[dict[str, str]]:
    return [_filter('cliente_contrato.id', '=', id_contrato)]


def build_filters_contratos_by_status(status: str = 'A') -> list[dict[str, str]]:
    return [_filter('cliente_contrato.status', '=', status)]


def build_filters_contas_em_aberto() -> list[dict[str, str]]:
    return [_filter('fn_areceber.valor_aberto', '>', '0')]


def build_filters_contas_atrasadas(
    cutoff_due_date: date,
    due_from: date | None = None,
    due_to: date | None = None,
    filial_id: str | None = None,
) -> list[dict[str, str]]:
    filters = [
        _filter('fn_areceber.valor_aberto', '>', '0'),
        _filter('fn_areceber.data_vencimento', '<=', cutoff_due_date.strftime('%Y-%m-%d')),
    ]

    if due_from is not None:
        filters.append(_filter('fn_areceber.data_vencimento', '>=', due_from.strftime('%Y-%m-%d')))
    if due_to is not None:
        filters.append(_filter('fn_areceber.data_vencimento', '<=', due_to.strftime('%Y-%m-%d')))
    if filial_id is not None and filial_id.strip():
        filters.append(_filter('fn_areceber.filial_id', '=', filial_id.strip()))

    return filters


def build_filters_os_agendadas(start: date, end: date, tipo: str) -> list[dict[str, str]]:
    """
    TODO(ixc-field-mapping): confirmar TBs reais de data agendada/status/tipo em su_oss_chamado.
    Mantido parametrizado para facilitar ajuste por ambiente IXC.
    """
    return [
        _filter(TB_OS_DATA_AGENDADA, '>=', start.strftime('%Y-%m-%d')),
        _filter(TB_OS_DATA_AGENDADA, '<=', end.strftime('%Y-%m-%d')),
        _filter(TB_OS_TIPO, '=', tipo),
    ]


def build_filters_tickets_by_status(status: str) -> list[dict[str, str]]:
    """TODO(ixc-field-mapping): confirmar TB exato para status em su_ticket."""
    return [_filter(TB_TICKET_STATUS, '=', status)]
