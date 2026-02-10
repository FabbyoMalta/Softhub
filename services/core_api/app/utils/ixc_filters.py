from __future__ import annotations

from datetime import date
from typing import Any

SUPPORTED_OPS = {'=', '!=', '>', '<', '>=', '<=', 'LIKE', 'IN'}


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


def build_filters_contas_atrasadas(today: date) -> list[dict[str, str]]:
    return [
        _filter('fn_areceber.valor_aberto', '>', '0'),
        _filter('fn_areceber.data_vencimento', '<=', today.strftime('%Y-%m-%d')),
    ]


def build_filters_os_agendadas(start: date, end: date, tipo: str) -> list[dict[str, str]]:
    """
    TODO(ixc-field-mapping): confirmar TBs reais de data agendada/status/tipo em su_oss_chamado.
    Mantido parametrizado para facilitar ajuste por ambiente IXC.
    """
    return [
        _filter('su_oss_chamado.data_agendada', '>=', start.strftime('%Y-%m-%d')),
        _filter('su_oss_chamado.data_agendada', '<=', end.strftime('%Y-%m-%d')),
        _filter('su_oss_chamado.tipo', '=', tipo),
    ]


def build_filters_tickets_by_status(status: str) -> list[dict[str, str]]:
    """TODO(ixc-field-mapping): confirmar TB exato para status em su_ticket."""
    return [_filter('su_ticket.status', '=', status)]
