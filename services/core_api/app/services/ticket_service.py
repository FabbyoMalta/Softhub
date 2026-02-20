from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import httpx

from app.adapters.ixc_adapter import IXCAdapter
from app.clients.ixc_client import IXCClient, build_basic_auth_header
from app.config import get_settings
from app.db import BillingCase


class TicketServiceError(ValueError):
    pass


@dataclass
class TicketService:
    adapter: IXCAdapter

    def _require_enabled(self) -> None:
        s = get_settings()
        if not s.billing_ticket_enable:
            raise TicketServiceError('Ticket integration desabilitada (BILLING_TICKET_ENABLE=false)')
        missing = []
        if not s.billing_ticket_setor_id:
            missing.append('BILLING_TICKET_SETOR_ID')
        if not s.billing_ticket_assunto_id:
            missing.append('BILLING_TICKET_ASSUNTO_ID')
        if missing:
            raise TicketServiceError(f'Variáveis obrigatórias ausentes: {", ".join(missing)}')

    def _build_payload(self, case: BillingCase) -> dict[str, Any]:
        s = get_settings()
        payload: dict[str, Any] = {
            'tipo': 'C',
            'id_cliente': case.id_cliente,
            'id_filial': case.filial_id,
            'id_ticket_setor': s.billing_ticket_setor_id,
            'id_assunto': s.billing_ticket_assunto_id,
            'external_id': case.external_id,
            'titulo': f'Cobrança título {case.external_id}',
            'menssagem': (
                f'Título em aberto. cliente={case.id_cliente} contrato={case.id_contrato or "-"} '
                f'titulo={case.external_id} vencimento={case.due_date} dias={case.open_days} '
                f'valor={case.amount_open} filial={case.filial_id or "-"}'
            ),
            'prioridade': s.billing_ticket_prioridade,
            'su_status': 'N',
            'finalizar_atendimento': 'N',
        }
        if case.id_contrato:
            payload['id_contrato'] = case.id_contrato
        return payload

    def _create_ticket_real(self, payload: dict[str, Any]) -> str:
        s = get_settings()
        endpoint = s.billing_ticket_endpoint.strip('/')
        url = f"https://{s.ixc_host}/webservice/v1/{endpoint}"
        headers = {
            'Authorization': build_basic_auth_header(s.ixc_user, s.ixc_token),
            'Content-Type': 'application/json',
            'ixcsoft': 'inserir',
        }
        with httpx.Client(verify=s.ixc_verify_tls, timeout=s.ixc_timeout_s) as client:
            response = client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            data = response.json() if response.content else {}
        ticket_id = str(data.get('id') or data.get('ticket_id') or '')
        if not ticket_id:
            raise TicketServiceError('IXC não retornou ticket_id')
        return ticket_id

    def _close_ticket_real(self, ticket_id: str) -> None:
        s = get_settings()
        endpoint = s.billing_ticket_close_endpoint.strip('/')
        url = f"https://{s.ixc_host}/webservice/v1/{endpoint}/{ticket_id}"
        headers = {
            'Authorization': build_basic_auth_header(s.ixc_user, s.ixc_token),
            'Content-Type': 'application/json',
            'ixcsoft': 'editar',
        }
        payload = {
            'su_status': 'S',
            'finalizar_atendimento': 'S',
            'menssagem': 'Título quitado, encerrando automaticamente.',
        }
        with httpx.Client(verify=s.ixc_verify_tls, timeout=s.ixc_timeout_s) as client:
            response = client.put(url, headers=headers, json=payload)
            response.raise_for_status()

    def create_ticket(self, case: BillingCase) -> str:
        self._require_enabled()
        payload = self._build_payload(case)
        if get_settings().ixc_mode.lower() == 'real':
            return self._create_ticket_real(payload)
        result = self.adapter.create_billing_ticket(payload)
        ticket_id = str(result.get('ticket_id') or '')
        if not ticket_id:
            raise TicketServiceError('IXC mock não retornou ticket_id')
        return ticket_id

    def close_ticket(self, case: BillingCase) -> None:
        self._require_enabled()
        if not case.ticket_id:
            raise TicketServiceError('Case sem ticket_id para fechar')
        if get_settings().ixc_mode.lower() == 'real':
            self._close_ticket_real(case.ticket_id)
            return
        self.adapter.close_billing_ticket(case.ticket_id, {'su_status': 'S', 'finalizar_atendimento': 'S'})
