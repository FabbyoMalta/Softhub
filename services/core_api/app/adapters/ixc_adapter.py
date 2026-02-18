from __future__ import annotations

from datetime import date, timedelta
from random import Random
from typing import Any, Protocol

from app.clients.ixc_client import IXCClient, IXCClientError
from app.config import get_settings
from app.services.ixc_grid_builder import TB_OS_ID_CLIENTE
from app.utils.ixc_filters import build_filters_contas_atrasadas, build_filters_contas_em_aberto, build_filters_contrato_by_id


class IXCAdapter(Protocol):
    def list_contratos(self, filters: dict[str, Any] | None = None) -> list[dict[str, Any]]: ...

    def list_contratos_by_ids(self, ids: list[str]) -> list[dict[str, Any]]: ...

    def list_contas_receber_abertas(self) -> list[dict[str, Any]]: ...

    def list_contas_receber_atrasadas(
        self,
        min_days: int = 20,
        due_from: date | None = None,
        due_to: date | None = None,
        filial_id: str | None = None,
    ) -> list[dict[str, Any]]: ...

    def list_contas_receber_by_ids(self, external_ids: list[str]) -> list[dict[str, Any]]: ...

    def list_service_orders(self, grid_filters: list[dict[str, Any]]) -> list[dict[str, Any]]: ...

    def list_clientes_by_ids(self, ids: list[str]) -> list[dict[str, Any]]: ...

    def create_billing_ticket(self, payload: dict[str, Any]) -> dict[str, Any]: ...

    def close_billing_ticket(self, ticket_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]: ...


class RealIXCAdapter:
    ENDPOINT_CONTRATOS = '/cliente_contrato'
    ENDPOINT_OSS = '/su_oss_chamado'
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

    def list_contratos_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        uniq = [str(i).strip() for i in ids if str(i).strip()]
        if not uniq:
            return []
        out: list[dict[str, Any]] = []
        for i in range(0, len(uniq), 200):
            batch = uniq[i : i + 200]
            filters = [{'TB': 'cliente_contrato.id', 'OP': 'IN', 'P': ','.join(batch)}]
            out.extend(self.client.iterate_all(self.ENDPOINT_CONTRATOS, filters, sortname='id'))
        return out

    def list_contas_receber_abertas(self) -> list[dict[str, Any]]:
        return self.client.iterate_all(self.ENDPOINT_ARECEBER, build_filters_contas_em_aberto(), sortname='id')

    def list_contas_receber_atrasadas(
        self,
        min_days: int = 20,
        due_from: date | None = None,
        due_to: date | None = None,
        filial_id: str | None = None,
    ) -> list[dict[str, Any]]:
        cutoff_due_date = date.today() - timedelta(days=max(min_days, 0))
        filters = build_filters_contas_atrasadas(
            cutoff_due_date=cutoff_due_date,
            due_from=due_from,
            due_to=due_to,
            filial_id=filial_id,
        )
        return self.client.iterate_all(self.ENDPOINT_ARECEBER, filters, rp=1000, sortname='id')

    def list_contas_receber_by_ids(self, external_ids: list[str]) -> list[dict[str, Any]]:
        uniq = [str(i).strip() for i in external_ids if str(i).strip()]
        if not uniq:
            return []
        out: list[dict[str, Any]] = []
        for i in range(0, len(uniq), 200):
            batch = uniq[i : i + 200]
            filters = [{'TB': 'fn_areceber.id', 'OP': 'IN', 'P': ','.join(batch)}]
            out.extend(self.client.iterate_all(self.ENDPOINT_ARECEBER, filters, rp=1000, sortname='id'))
        return out

    def list_service_orders(self, grid_filters: list[dict[str, Any]]) -> list[dict[str, Any]]:
        return self.client.iterate_all(self.ENDPOINT_OSS, grid_filters, sortname='id')

    def list_clientes_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        endpoint = f"/{get_settings().ixc_client_endpoint.strip('/')}"
        uniq = [str(i).strip() for i in ids if str(i).strip()]
        if not uniq:
            return []

        out: list[dict[str, Any]] = []
        try:
            for i in range(0, len(uniq), 200):
                batch = uniq[i : i + 200]
                in_filter = [{'TB': 'cliente.id', 'OP': 'IN', 'P': ','.join(batch)}]
                out.extend(self.client.iterate_all(endpoint, in_filter, sortname='id'))
            if out:
                return out
        except IXCClientError:
            pass

        for idx in range(0, len(uniq), 50):
            batch = uniq[idx : idx + 50]
            for cid in batch:
                filters = [{'TB': 'cliente.id', 'OP': '=', 'P': cid}]
                rows = self.client.iterate_all(endpoint, filters, sortname='id')
                if rows:
                    out.append(rows[0])
        return out

    def create_billing_ticket(self, payload: dict[str, Any]) -> dict[str, Any]:
        settings = get_settings()
        endpoint = settings.billing_ticket_endpoint
        if not endpoint:
            raise IXCClientError('BILLING_TICKET_ENDPOINT não configurado')
        response = self.client.post_list(
            endpoint=f"/{endpoint.strip('/')}",
            grid_filters=[],
            page=1,
            rp=1,
            sortname='id',
            sortorder='asc',
            action=settings.billing_ticket_action,
        )
        if not isinstance(response, dict):
            raise IXCClientError('Resposta inválida ao criar ticket')
        ticket_id = str(response.get('id') or response.get('ticket_id') or '')
        return {'ticket_id': ticket_id, 'raw': response, 'payload': payload}

    def close_billing_ticket(self, ticket_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        settings = get_settings()
        endpoint = settings.billing_ticket_close_endpoint
        if not endpoint:
            raise IXCClientError('BILLING_TICKET_CLOSE_ENDPOINT não configurado')
        response = self.client.post_list(
            endpoint=f"/{endpoint.strip('/')}",
            grid_filters=[],
            page=1,
            rp=1,
            sortname='id',
            sortorder='asc',
            action=settings.billing_ticket_close_action,
        )
        return {'ticket_id': ticket_id, 'raw': response, 'payload': payload or {}}


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
                'data_ativacao': '2024-01-10',
            },
            {
                'id': '3',
                'id_cliente': '101',
                'id_vendedor': '10',
                'status': 'A',
                'status_internet': 'CM',
                'situacao_financeira_contrato': 'N',
                'pago_ate_data': '2025-01-20',
                'contrato': 'Fibra 300Mb',
                'data_ativacao': '2024-05-01',
            },
        ]
        if filters and filters.get('id'):
            return [c for c in contratos if c['id'] == str(filters['id'])]
        return contratos

    def list_contratos_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        wanted = {str(i) for i in ids}
        return [c for c in self.list_contratos() if str(c.get('id')) in wanted]

    def list_contas_receber_abertas(self) -> list[dict[str, Any]]:
        return [
            {
                'id': '9001',
                'id_contrato': '2',
                'id_cliente': '100',
                'filial_id': '1',
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
                'id_contrato_avulso': '3',
                'id_cliente': '101',
                'filial_id': '2',
                'data_vencimento': '2026-01-15',
                'valor_aberto': '89.90',
                'valor': '89.90',
                'status': 'A',
                'tipo_recebimento': 'PIX',
                'linha_digitavel': '',
            },
        ]

    def list_contas_receber_atrasadas(
        self,
        min_days: int = 20,
        due_from: date | None = None,
        due_to: date | None = None,
        filial_id: str | None = None,
    ) -> list[dict[str, Any]]:
        cutoff = date.today() - timedelta(days=max(min_days, 0))
        rows = [r for r in self.list_contas_receber_abertas() if r.get('valor_aberto') not in {'0', '0.00'}]

        out: list[dict[str, Any]] = []
        for row in rows:
            due_raw = str(row.get('data_vencimento') or '')
            try:
                due = date.fromisoformat(due_raw)
            except ValueError:
                continue
            if due > cutoff:
                continue
            if due_from and due < due_from:
                continue
            if due_to and due > due_to:
                continue
            if filial_id and str(row.get('filial_id') or '').strip() != filial_id:
                continue
            out.append(row)
        return out

    def list_contas_receber_by_ids(self, external_ids: list[str]) -> list[dict[str, Any]]:
        wanted = {str(i) for i in external_ids}
        return [r for r in self.list_contas_receber_abertas() if str(r.get('id')) in wanted]

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
                    'id_filial': '1' if idx % 2 == 0 else '2',
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
                'su_oss_chamado.id_filial': 'id_filial',
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

    def list_clientes_by_ids(self, ids: list[str]) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for cid in ids:
            out.append(
                {
                    'id': str(cid),
                    'nome': f'Cliente {cid}',
                    'razao_social': f'Cliente {cid} LTDA',
                    'cidade': ['Vila Velha', 'Vitória', 'Serra'][int(cid) % 3] if str(cid).isdigit() else 'Vitória',
                    'bairro': ['Centro', 'Praia', 'Jardim'][int(cid) % 3] if str(cid).isdigit() else 'Centro',
                    'endereco': f'Av. Cliente {cid}',
                    'telefone': f'2799999{int(cid)%1000:03d}' if str(cid).isdigit() else '2799999000',
                }
            )
        return out

    def create_billing_ticket(self, payload: dict[str, Any]) -> dict[str, Any]:
        external_id = str(payload.get('external_id') or payload.get('titulo_id') or '0')
        return {'ticket_id': f'TCK-{external_id}', 'payload': payload}

    def close_billing_ticket(self, ticket_id: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        return {'ticket_id': ticket_id, 'status': 'CLOSED', 'payload': payload or {}}
