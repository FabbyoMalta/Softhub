from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from app.adapters.ixc_adapter import IXCAdapter
from app.services.ixc_grid_builder import expand_os_query_grids

STATUS_LABELS = {
    'A': 'Aberta',
    'AN': 'Análise',
    'EN': 'Encaminhada',
    'AS': 'Assumida',
    'AG': 'Agendada',
    'DS': 'Deslocamento',
    'EX': 'Execução',
    'F': 'Finalizada',
    'RAG': 'Aguardando agendamento',
}
STATUS_GROUPS = {
    'open_like': ['A', 'AN', 'EN', 'AS', 'DS', 'EX', 'RAG'],
    'scheduled': ['AG', 'RAG', 'AS', 'DS', 'EX'],
    'done': ['F'],
}
ASSUNTO_CATEGORIES = {
    '1': 'instalacao',
    '15': 'mudanca_endereco',
    '17': 'sem_conexao',
    '34': 'quedas_constantes',
    '31': 'analise_suporte',
}
INSTALL_ASSUNTOS = {'1'}
MAINTENANCE_ASSUNTOS = {'17', '34', '31'}
SAO_PAULO_TZ = ZoneInfo('America/Sao_Paulo')


def parse_date_or_default(raw: str | None, default: date) -> date:
    if not raw:
        return default
    return datetime.strptime(raw, '%Y-%m-%d').date()


def _parse_dt(raw: str | None) -> datetime | None:
    if not raw:
        return None
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(raw[:19], fmt)
        except Exception:
            pass
    return None


def agenda_week_range(start_raw: str | None, days: int) -> tuple[date, date]:
    start = parse_date_or_default(start_raw, date.today())
    total_days = max(1, min(days, 31))
    return start, start + timedelta(days=total_days - 1)


def maintenances_range(from_raw: str | None, to_raw: str | None) -> tuple[date, date]:
    default_start = date.today() - timedelta(days=7)
    default_end = date.today() + timedelta(days=7)
    start = parse_date_or_default(from_raw, default_start)
    end = parse_date_or_default(to_raw, default_end)
    return (start, end) if start <= end else (end, start)


def resolve_definition(definition_json: dict[str, Any] | None, scope: str) -> dict[str, Any]:
    d = dict(definition_json or {})
    category = d.get('category')
    if category == 'instalacao':
        d['assunto_ids'] = sorted(INSTALL_ASSUNTOS)
    elif category == 'manutencao':
        d['assunto_ids'] = sorted(MAINTENANCE_ASSUNTOS)

    if not d.get('status_codes'):
        if scope == 'agenda_week':
            d['status_codes'] = STATUS_GROUPS['scheduled']
        else:
            merged = STATUS_GROUPS['open_like'] + STATUS_GROUPS['scheduled']
            d['status_codes'] = sorted(set(merged))

    if scope == 'maintenances' and not d.get('assunto_ids'):
        d['assunto_ids'] = sorted(MAINTENANCE_ASSUNTOS)

    return d


def _infer_type(assunto_id: str) -> str:
    if assunto_id in INSTALL_ASSUNTOS:
        return 'instalacao'
    if assunto_id in MAINTENANCE_ASSUNTOS:
        return 'manutencao'
    return 'outros'


def _extract_customer_name(c: dict[str, Any]) -> str | None:
    return c.get('razao') or c.get('razao_social') or c.get('nome') or c.get('fantasia')


def normalize_row(row: dict[str, Any], customer: dict[str, Any] | None) -> dict[str, Any]:
    c = customer or {}
    scheduled_at = row.get('data_agenda')
    dt = _parse_dt(scheduled_at)
    assunto_id = str(row.get('id_assunto') or '')
    status_code = str(row.get('status') or '')
    return {
        'id': str(row.get('id') or ''),
        'scheduled_at': scheduled_at,
        'date': dt.strftime('%Y-%m-%d') if dt else (scheduled_at or '')[:10],
        'time': dt.strftime('%H:%M') if dt else None,
        'status_code': status_code,
        'status_label': STATUS_LABELS.get(status_code, status_code),
        'assunto_id': assunto_id,
        'type': _infer_type(assunto_id),
        'id_cliente': str(row.get('id_cliente') or ''),
        'customer_name': _extract_customer_name(c),
        'phone': c.get('telefone') or c.get('whatsapp') or c.get('celular'),
        'address': row.get('endereco') or c.get('endereco'),
        'bairro': row.get('bairro') or c.get('bairro'),
        'cidade': c.get('cidade') or row.get('cidade'),
        'protocolo': str(row.get('protocolo') or ''),
        'source': 'ixc',
    }


def _fetch_order_rows(
    adapter: IXCAdapter,
    date_start: date,
    date_end: date,
    statuses: list[str],
    assunto_ids: list[str],
) -> list[dict[str, Any]]:
    grids = expand_os_query_grids(date_start, date_end, statuses, assunto_ids, use_in=False)
    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for grid in grids:
        for row in adapter.list_service_orders(grid):
            key = str(row.get('id') or '')
            if key and key not in seen:
                seen.add(key)
                rows.append(row)
    return rows


def fetch_dashboard_items(
    adapter: IXCAdapter,
    scope: str,
    date_start: date,
    date_end: date,
    definition_json: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    definition = resolve_definition(definition_json, scope)
    statuses = [str(x) for x in definition.get('status_codes') or []]
    assunto_ids = [str(x) for x in definition.get('assunto_ids') or []]

    rows = _fetch_order_rows(adapter, date_start, date_end, statuses, assunto_ids)

    ids = sorted({str(r.get('id_cliente')) for r in rows if r.get('id_cliente')})
    clientes = adapter.list_clientes_by_ids(ids) if ids else {}

    return [normalize_row(r, clientes.get(str(r.get('id_cliente') or ''))) for r in rows]


def _resolve_today(today: str | None) -> date:
    if today:
        return parse_date_or_default(today, datetime.now(SAO_PAULO_TZ).date())
    return datetime.now(SAO_PAULO_TZ).date()


def _is_same_day(raw: str | None, reference: date) -> bool:
    dt = _parse_dt(raw)
    if not dt:
        return False
    return dt.date() == reference


def build_dashboard_summary(
    adapter: IXCAdapter,
    date_start: date,
    days: int,
    definition_json: dict[str, Any] | None,
    today: str | None = None,
) -> dict[str, Any]:
    total_days = max(1, min(days, 31))
    date_end = date_start + timedelta(days=total_days - 1)
    today_date = _resolve_today(today)
    definition = dict(definition_json or {})

    install_rows = _fetch_order_rows(
        adapter,
        date_start,
        date_end,
        STATUS_GROUPS['open_like'] + STATUS_GROUPS['scheduled'] + STATUS_GROUPS['done'],
        sorted(INSTALL_ASSUNTOS),
    )
    maint_rows = _fetch_order_rows(
        adapter,
        date_start,
        date_end,
        STATUS_GROUPS['open_like'] + STATUS_GROUPS['scheduled'] + STATUS_GROUPS['done'],
        sorted(MAINTENANCE_ASSUNTOS),
    )

    selected_statuses = {str(s) for s in definition.get('status_codes') or []}
    if selected_statuses:
        install_rows = [r for r in install_rows if str(r.get('status') or '') in selected_statuses]
        maint_rows = [r for r in maint_rows if str(r.get('status') or '') in selected_statuses]

    summary = {
        'period': {
            'start': date_start.strftime('%Y-%m-%d'),
            'end': date_end.strftime('%Y-%m-%d'),
        },
        'instalacoes': {
            'agendadas_hoje': sum(
                1
                for r in install_rows
                if str(r.get('status') or '') in STATUS_GROUPS['scheduled'] and _is_same_day(r.get('data_agenda'), today_date)
            ),
            'finalizadas_hoje': sum(
                1
                for r in install_rows
                if str(r.get('status') or '') in STATUS_GROUPS['done']
                and _is_same_day(r.get('data_fechamento') or r.get('data_final') or r.get('data_agenda'), today_date)
            ),
            'total_periodo': len(install_rows),
        },
        'manutencoes': {
            'abertas_total': sum(1 for r in maint_rows if str(r.get('status') or '') in STATUS_GROUPS['open_like']),
            'abertas_hoje': sum(
                1
                for r in maint_rows
                if str(r.get('status') or '') in STATUS_GROUPS['open_like']
                and (_is_same_day(r.get('data_agenda'), today_date) or _is_same_day(r.get('data_abertura'), today_date))
            ),
            'finalizadas_hoje': sum(
                1
                for r in maint_rows
                if str(r.get('status') or '') in STATUS_GROUPS['done']
                and _is_same_day(r.get('data_fechamento') or r.get('data_final') or r.get('data_agenda'), today_date)
            ),
            'total_periodo': len(maint_rows),
        },
    }
    return summary
