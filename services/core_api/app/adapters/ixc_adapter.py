from __future__ import annotations

from datetime import date
from typing import Any, Protocol

from app.clients.ixc_client import IXCClient
from app.utils.ixc_filters import (
    build_filters_contas_em_aberto,
    build_filters_contrato_by_id,
)


class IXCAdapter(Protocol):
    def list_contratos(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...

    def list_contas_receber_abertas(self) -> list[dict[str, Any]]: ...


class RealIXCAdapter:
    ENDPOINT_CONTRATOS = '/cliente_contrato'
    ENDPOINT_OSS = '/su_oss_chamado'
    ENDPOINT_TICKETS = '/su_ticket'
    ENDPOINT_ARECEBER = '/fn_areceber'

    def __init__(self, client: IXCClient) -> None:
        self.client = client

    def list_contratos(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        grid_filters: list[dict[str, Any]] = []
        if filters and filters.get('id') is not None:
            grid_filters = build_filters_contrato_by_id(filters['id'])
        elif filters and filters.get('status') is not None:
            grid_filters = [{'TB': 'cliente_contrato.status', 'OP': '=', 'P': str(filters['status'])}]
        return self.client.iterate_all(self.ENDPOINT_CONTRATOS, grid_filters, sortname='id')

    def list_contas_receber_abertas(self) -> list[dict[str, Any]]:
        return self.client.iterate_all(
            self.ENDPOINT_ARECEBER,
            build_filters_contas_em_aberto(),
            sortname='id',
        )

    def list_oss_agendadas(self, start: date, end: date, tipo: str) -> list[dict[str, Any]]:
        """TODO(ixc-field-mapping): ajustar grid filters reais de OS por ambiente."""
        return self.client.iterate_all(self.ENDPOINT_OSS, [], sortname='id')

    def list_tickets_by_status(self, status: str) -> list[dict[str, Any]]:
        """TODO(ixc-field-mapping): ajustar grid filters reais de ticket por ambiente."""
        return self.client.iterate_all(self.ENDPOINT_TICKETS, [], sortname='id')


class MockIXCAdapter:
    def list_contratos(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        contratos = [
            {
                'id': '2',
                'id_cliente': '100',
                'id_vendedor': '12',
                'status': 'A',
                'status_internet': 'A',
                'situacao_financeira_contrato': 'R',
                'pago_ate_data': '2026-01-20',
                'contrato': 'Fibra 600Mb',
            }
        ]
        if filters and filters.get('id'):
            return [c for c in contratos if c['id'] == str(filters['id'])]
        return contratos

    def list_contas_receber_abertas(self) -> list[dict[str, Any]]:
        return [
            {
                'id': '9001',
                'id_contrato': '2',
                'id_cliente': '100',
                'data_vencimento': '2026-01-01',
                'valor_aberto': '149.90',
                'valor': '149.90',
                'status': 'A',
                'tipo_recebimento': 'Boleto',
                'linha_digitavel': '00190.00009 12345.678901 23456.789012 3 98760000014990',
            },
            {
                'id': '9002',
                'id_contrato': '',
                'id_cliente': '101',
                'data_vencimento': '2026-01-15',
                'valor_aberto': '89.90',
                'valor': '89.90',
                'status': 'A',
                'tipo_recebimento': 'PIX',
                'linha_digitavel': '',
            },
        ]
