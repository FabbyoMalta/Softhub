from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter

from sqlalchemy import or_, select

from app.adapters.ixc_adapter import IXCAdapter
from app.db import BillingCase, SessionLocal


@dataclass
class BillingEnrichResult:
    updated: int
    duration_ms: float


def _pick_contract_id(snapshot_json: dict | None) -> tuple[str | None, bool]:
    snapshot = snapshot_json or {}
    id_contrato = str(snapshot.get('id_contrato') or '').strip()
    if id_contrato and id_contrato != '0':
        return id_contrato, False

    id_contrato_avulso = str(snapshot.get('id_contrato_avulso') or '').strip()
    if id_contrato_avulso and id_contrato_avulso != '0':
        return id_contrato_avulso, False

    return None, True


def enrich_billing_cases(adapter: IXCAdapter, limit: int = 2000, only_missing: bool = True) -> BillingEnrichResult:
    started = perf_counter()

    with SessionLocal() as db:
        query = select(BillingCase).where(BillingCase.status_case == 'OPEN')
        if only_missing:
            query = query.where(
                or_(
                    BillingCase.contract_json.is_(None),
                    BillingCase.client_json.is_(None),
                    BillingCase.id_contrato.is_(None),
                )
            )

        rows = list(db.scalars(query.order_by(BillingCase.last_seen_at.desc()).limit(max(1, limit))))
        if not rows:
            return BillingEnrichResult(updated=0, duration_ms=round((perf_counter() - started) * 1000, 2))

        contract_ids: set[str] = set()
        client_ids: set[str] = set()
        selected_contract_by_case: dict[str, str | None] = {}
        missing_contract_by_case: dict[str, bool] = {}

        for case in rows:
            cid, missing = _pick_contract_id(case.snapshot_json)
            selected_contract_by_case[case.id] = cid
            missing_contract_by_case[case.id] = missing
            if cid:
                contract_ids.add(cid)
            if case.id_cliente:
                client_ids.add(case.id_cliente)

        contracts = adapter.list_contratos_by_ids(sorted(contract_ids)) if contract_ids else []
        contracts_by_id = {str(c.get('id')): c for c in contracts if c.get('id') is not None}
        clients = adapter.list_clientes_by_ids(sorted(client_ids)) if client_ids else []
        clients_by_id = {str(c.get('id')): c for c in clients if c.get('id') is not None}

        updated = 0
        for case in rows:
            cid = selected_contract_by_case.get(case.id)
            contract = contracts_by_id.get(str(cid)) if cid else None
            client = clients_by_id.get(str(case.id_cliente))

            case.id_contrato = cid
            case.contract_missing = missing_contract_by_case.get(case.id, False)
            case.contract_json = (
                {
                    'status': contract.get('status'),
                    'status_internet': contract.get('status_internet'),
                    'situacao_financeira': contract.get('situacao_financeira_contrato'),
                    'pago_ate_data': contract.get('pago_ate_data'),
                    'id_vendedor': contract.get('id_vendedor'),
                    'plano_nome': contract.get('contrato'),
                    'data_ativacao': contract.get('data_ativacao'),
                }
                if contract
                else None
            )
            case.client_json = (
                {
                    'nome': client.get('nome') or client.get('razao_social'),
                    'telefone': client.get('telefone') or client.get('fone'),
                    'endereco': client.get('endereco') or client.get('logradouro'),
                    'bairro': client.get('bairro'),
                    'cidade': client.get('cidade'),
                }
                if client
                else None
            )
            updated += 1

        db.commit()
        return BillingEnrichResult(updated=updated, duration_ms=round((perf_counter() - started) * 1000, 2))
