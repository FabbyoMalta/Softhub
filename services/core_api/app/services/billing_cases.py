from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from app.adapters.ixc_adapter import IXCAdapter


@dataclass
class _AggCase:
    case_key: str
    id_cliente: str
    id_contrato: str | None
    cliente_nome: str | None
    qtd_titulos: int
    total_aberto: Decimal
    oldest_due_date: date | None
    newest_due_date: date | None
    max_open_days: int
    titles: list[dict[str, Any]]


def _parse_date(raw: Any) -> date | None:
    value = str(raw or '').strip()
    if not value or value == '0000-00-00':
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except ValueError:
        return None


def _to_decimal(raw: Any) -> Decimal:
    try:
        return Decimal(str(raw or '0'))
    except Exception:
        return Decimal('0')


def _normalize_contract_id(row: dict[str, Any]) -> str | None:
    c1 = str(row.get('id_contrato') or '').strip()
    if c1 and c1 != '0':
        return c1
    c2 = str(row.get('id_contrato_avulso') or '').strip()
    if c2 and c2 != '0':
        return c2
    return None


def build_grouped_billing_cases(
    adapter: IXCAdapter,
    only_20p: bool = True,
    group_by: str = 'contract',
    limit: int = 500,
    min_due_date: date | None = None,
    max_due_date: date | None = None,
) -> dict[str, Any]:
    today = date.today()

    if only_20p:
        rows = adapter.list_contas_receber_atrasadas(min_days=20, due_from=min_due_date, due_to=max_due_date)
    else:
        due_from = min_due_date or (today.replace(day=1))
        rows = adapter.list_contas_receber_para_sync(
            due_from=due_from,
            only_open=True,
            rp=500,
            limit_pages=5,
        )

    filtered_rows: list[dict[str, Any]] = []
    for row in rows:
        due = _parse_date(row.get('data_vencimento'))
        amount_open = _to_decimal(row.get('valor_aberto'))
        if due is None or amount_open <= 0:
            continue
        if min_due_date and due < min_due_date:
            continue
        if max_due_date and due > max_due_date:
            continue

        open_days = max(0, (today - due).days)
        title = {
            'external_id': str(row.get('id') or ''),
            'due_date': due.isoformat(),
            'issue_date': str(row.get('data_emissao') or '') or None,
            'amount_open': str(amount_open),
            'amount_total': str(row.get('valor') or ''),
            'payment_type': row.get('tipo_recebimento'),
            'open_days': open_days,
            'status': row.get('status'),
            'id_cobranca': str(row.get('id_cobranca') or '') or None,
            'linha_digitavel': row.get('linha_digitavel'),
            'id_cliente': str(row.get('id_cliente') or ''),
            'id_contrato_norm': _normalize_contract_id(row),
        }
        filtered_rows.append(title)

    client_ids = sorted({r['id_cliente'] for r in filtered_rows if r['id_cliente']})
    clients = adapter.list_clientes_by_ids(client_ids) if client_ids else []
    client_map = {str(c.get('id') or c.get('id_cliente') or ''): c for c in clients if (c.get('id') or c.get('id_cliente'))}

    grouped: dict[str, _AggCase] = {}
    for t in filtered_rows:
        contract_id = t['id_contrato_norm']
        id_cliente = t['id_cliente']

        if group_by == 'client':
            key = f'cliente:{id_cliente}'
        else:
            key = f'cliente:{id_cliente}|contrato:{contract_id or "-"}'

        due = _parse_date(t['due_date'])
        amount_open = _to_decimal(t['amount_open'])
        agg = grouped.get(key)
        if agg is None:
            c = client_map.get(id_cliente, {})
            grouped[key] = _AggCase(
                case_key=key,
                id_cliente=id_cliente,
                id_contrato=contract_id,
                cliente_nome=c.get('nome') or c.get('razao_social') or c.get('fantasia'),
                qtd_titulos=0,
                total_aberto=Decimal('0'),
                oldest_due_date=due,
                newest_due_date=due,
                max_open_days=int(t['open_days']),
                titles=[],
            )
            agg = grouped[key]

        agg.qtd_titulos += 1
        agg.total_aberto += amount_open
        agg.max_open_days = max(agg.max_open_days, int(t['open_days']))
        if due and (agg.oldest_due_date is None or due < agg.oldest_due_date):
            agg.oldest_due_date = due
        if due and (agg.newest_due_date is None or due > agg.newest_due_date):
            agg.newest_due_date = due
        agg.titles.append({k: v for k, v in t.items() if k not in {'id_cliente', 'id_contrato_norm'}})

    cases = list(grouped.values())
    for c in cases:
        c.titles.sort(key=lambda x: (x.get('due_date') or '9999-12-31', x.get('external_id') or ''))

    if only_20p:
        cases = [c for c in cases if c.max_open_days >= 20]

    cases.sort(key=lambda c: (c.max_open_days, c.total_aberto), reverse=True)
    cases = cases[: max(1, limit)]

    all_oldest = [c.oldest_due_date for c in cases if c.oldest_due_date]
    amount_open_total = sum((c.total_aberto for c in cases), Decimal('0'))
    titles_total = sum(c.qtd_titulos for c in cases)
    cases_20p = sum(1 for c in cases if c.max_open_days >= 20)

    return {
        'summary': {
            'cases_total': len(cases),
            'cases_20p': cases_20p,
            'titles_total': titles_total,
            'amount_open_total': str(amount_open_total),
            'oldest_due_date': min(all_oldest).isoformat() if all_oldest else None,
            'generated_at': datetime.utcnow().isoformat(),
        },
        'cases': [
            {
                'case_key': c.case_key,
                'id_cliente': c.id_cliente,
                'id_contrato': c.id_contrato,
                'cliente_nome': c.cliente_nome,
                'qtd_titulos': c.qtd_titulos,
                'total_aberto': str(c.total_aberto),
                'oldest_due_date': c.oldest_due_date.isoformat() if c.oldest_due_date else None,
                'newest_due_date': c.newest_due_date.isoformat() if c.newest_due_date else None,
                'max_open_days': c.max_open_days,
                'titles': c.titles,
            }
            for c in cases
        ],
    }
