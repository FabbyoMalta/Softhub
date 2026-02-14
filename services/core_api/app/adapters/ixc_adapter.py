from __future__ import annotations

from datetime import date, timedelta
from random import Random
from typing import Any, Protocol

from app.clients.ixc_client import IXCClient, IXCClientError
from app.services.ixc_grid_builder import TB_OS_ID_CLIENTE
from app.utils.ixc_filters import build_filters_contas_em_aberto, build_filters_contrato_by_id


class IXCAdapter(Protocol):
    def list_contratos(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...

    def list_contas_receber_abertas(self) -> list[dict[str, Any]]: ...

    def list_service_orders(self, grid_filters: list[dict[str, Any]]) -> list[dict[str, Any]]: ...

    def list_clientes_by_ids(self, ids: list[str]) -> dict[str, dict[str, Any]]: ...


class RealIXCAdapter:
    ENDPOINT_CONTRATOS = '/cliente_contrato'
    ENDPOINT_OSS = '/su_oss_chamado'
    ENDPOINT_ARECEBER = '/fn_areceber'
    CLIENT_ENDPOINT = '/cliente'  # TODO: confirmar endpoint por ambiente

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
        return self.client.iterate_all(self.ENDPOINT_ARECEBER, build_filters_contas_em_aberto(), sortname='id')

    def list_service_orders(self, grid_filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self.client.iterate_all(self.ENDPOINT_OSS, grid_filters, sortname='id')

    def list_clientes_by_ids(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        cache: dict[str, dict[str, Any]] = {}
        uniq = [str(i) for i in ids if str(i).strip()]
        if not uniq:
            return cache

        try:
            in_filter = [{'TB': TB_OS_ID_CLIENTE.replace('su_oss_chamado', 'cliente'), 'OP': 'IN', 'P': ','.join(uniq)}]
            rows = self.client.iterate_all(self.CLIENT_ENDPOINT, in_filter, sortname='id')
            for row in rows:
                rid = str(row.get('id') or row.get('id_cliente') or '')
                if rid:
                    cache[rid] = row
            if cache:
                return cache
        except IXCClientError:
            pass

        for idx in range(0, len(uniq), 50):
            batch = uniq[idx : idx + 50]
            for cid in batch:
                filters = [{'TB': 'cliente.id', 'OP': '=', 'P': cid}]
                rows = self.client.iterate_all(self.CLIENT_ENDPOINT, filters, sortname='id')
                if rows:
                    cache[cid] = rows[0]
        return cache


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
        statuses = ['A', 'AN', 'EN', 'AS', 'AG', 'DS', 'EX', 'F', 'RAG']
        assuntos = ['1', '15', '17', '34', '31', '99']
        rows: list[dict[str, Any]] = []
        today = date.today()
        for idx in range(80):
            d = today - timedelta(days=10) + timedelta(days=idx % 24)
            rows.append(
                {
                    'id': f'OS-{1000 + idx}',
                    'id_cliente': str(500 + (idx % 15)),
                    'id_assunto': assuntos[idx % len(assuntos)],
                    'status': statuses[idx % len(statuses)],
                    'data_agenda': f"{d.strftime('%Y-%m-%d')} {8 + (idx % 10):02d}:{(idx % 2) * 30:02d}:00",
                    'data_abertura': f"{(d - timedelta(days=1)).strftime('%Y-%m-%d')} 09:00:00",
                    'data_fechamento': f"{(d + timedelta(days=1)).strftime('%Y-%m-%d')} 18:00:00" if statuses[idx % len(statuses)] == 'F' else None,
                    'endereco': f'Rua {idx}, {10 + idx}',
                    'bairro': ['Centro', 'Praia', 'Jardim', 'Industrial'][idx % 4],
                    'protocolo': f'P{10000+idx}',
                    'mensagem': ['ONU', 'Sem conexão', 'Suporte', 'Mudança'][rng.randrange(0, 4)],
                }
            )

        def _match(row: dict[str, Any], f: dict[str, Any]) -> bool:
            tb, op, p = f.get('TB'), f.get('OP'), str(f.get('P') or '')
            field_map = {
                'su_oss_chamado.data_agenda': 'data_agenda',
                'su_oss_chamado.status': 'status',
                'su_oss_chamado.id_assunto': 'id_assunto',
                'su_oss_chamado.id_cliente': 'id_cliente',
                'su_oss_chamado.data_abertura': 'data_abertura',
                'su_oss_chamado.data_fechamento': 'data_fechamento',
            }
            v = str(row.get(field_map.get(tb, ''), ''))
            if op == '=':
                return v == p
            if op == 'IN':
                return v in [x.strip() for x in p.split(',') if x.strip()]
            if op == '>=':
                return v >= p
            if op == '<=':
                return v <= p
            return True

        out = rows
        for f in grid_filters:
            out = [r for r in out if _match(r, f)]
        return out

    def list_clientes_by_ids(self, ids: list[str]) -> dict[str, dict[str, Any]]:
        data: dict[str, dict[str, Any]] = {}
        for cid in ids:
            data[str(cid)] = {
                'id': str(cid),
                'nome': f'Cliente {cid}',
                'cidade': ['Vila Velha', 'Vitória', 'Serra'][int(cid) % 3],
                'bairro': ['Centro', 'Praia', 'Jardim'][int(cid) % 3],
                'endereco': f'Av. Cliente {cid}',
                'telefone': f'2799999{int(cid)%1000:03d}',
            }
        return data
