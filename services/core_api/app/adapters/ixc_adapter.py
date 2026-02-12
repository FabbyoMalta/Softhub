from __future__ import annotations

from datetime import date, timedelta
from random import Random
from typing import Any, Protocol

from app.clients.ixc_client import IXCClient
from app.services.ixc_grid_builder import (
    TB_OS_ASSUNTO,
    TB_OS_CIDADE,
    TB_OS_DATA_AGENDADA,
    TB_OS_STATUS,
    TB_OS_TIPO,
)
from app.utils.ixc_filters import build_filters_contas_em_aberto, build_filters_contrato_by_id


class IXCAdapter(Protocol):
    def list_contratos(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...

    def list_contas_receber_abertas(self) -> list[dict[str, Any]]: ...

    def list_service_orders(self, grid_filters: list[dict[str, Any]]) -> list[dict[str, Any]]: ...


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

    def list_service_orders(self, grid_filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self.client.iterate_all(self.ENDPOINT_OSS, grid_filters, sortname='id')


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

    def list_service_orders(self, grid_filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
        rng = Random(42)
        statuses = ['aberta', 'agendada', 'finalizada']
        cities = ['Vila Velha', 'Vitória', 'Serra', 'Cariacica']
        neighborhoods = ['Centro', 'Praia', 'Jardim', 'Industrial']
        assuntos = ['ONU sem sinal', 'Troca de roteador', 'Instalação comercial', 'Mudança de endereço']

        today = date.today()
        all_rows: list[dict[str, Any]] = []
        for idx in range(60):
            scheduled = today - timedelta(days=10) + timedelta(days=idx % 21)
            os_type = 'manutencao' if idx % 3 else 'instalacao'
            all_rows.append(
                {
                    'id': f'OS-{1000 + idx}',
                    'data_agendada': scheduled.strftime('%Y-%m-%d'),
                    'hora_agendada': f'{8 + (idx % 9):02d}:{(idx % 2) * 30:02d}',
                    'tipo': os_type,
                    'status': statuses[idx % len(statuses)],
                    'id_cliente': f'C{3000 + idx}',
                    'cliente': f'Cliente {idx}',
                    'cidade': cities[idx % len(cities)],
                    'bairro': neighborhoods[idx % len(neighborhoods)],
                    'endereco': f'Rua {idx}, {10 + idx}',
                    'assunto': assuntos[rng.randrange(0, len(assuntos))],
                }
            )

        def match(row: dict[str, Any], gf: dict[str, Any]) -> bool:
            tb = gf.get('TB')
            op = gf.get('OP')
            param = str(gf.get('P') or '')

            value_map = {
                TB_OS_DATA_AGENDADA: row.get('data_agendada', ''),
                TB_OS_TIPO: row.get('tipo', ''),
                TB_OS_STATUS: row.get('status', ''),
                TB_OS_CIDADE: row.get('cidade', ''),
                TB_OS_ASSUNTO: row.get('assunto', ''),
            }
            value = str(value_map.get(tb, ''))

            if op == '=':
                return value.lower() == param.lower()
            if op == '!=':
                return value.lower() != param.lower()
            if op == 'LIKE':
                needle = param.replace('%', '').lower()
                return needle in value.lower()
            if op == '>=':
                return value >= param
            if op == '<=':
                return value <= param
            return True

        filtered = all_rows
        for gf in grid_filters:
            filtered = [row for row in filtered if match(row, gf)]
        return filtered
