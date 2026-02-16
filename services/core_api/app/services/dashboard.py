from __future__ import annotations

from datetime import date, datetime, timedelta
import logging
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.adapters.ixc_adapter import IXCAdapter
from app.services.ixc_grid_builder import TB_OS_ID_ASSUNTO, TB_OS_ID_FILIAL, TB_OS_STATUS, expand_os_query_grids
from app.services.settings import get_settings_payload

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
MAINTENANCE_TAB_STATUS = {
    'open': ['A', 'AN', 'EN', 'AS', 'DS', 'EX', 'AG', 'RAG'],
    'scheduled': ['AG', 'RAG'],
    'done': ['F'],
}
DEFAULT_INSTALL_ASSUNTOS = {'1', '15'}
DEFAULT_MAINTENANCE_ASSUNTOS = {'17', '34', '31'}
DEFAULT_SUMMARY_TZ = 'America/Sao_Paulo'
WEEKDAY_KEYS = ['mon', 'tue', 'wed', 'thu', 'fri', 'sat', 'sun']
CAPACITY_STATUS_CODES = ['AG', 'RAG', 'AS', 'DS', 'EX', 'F', 'A', 'AN', 'EN']
logger = logging.getLogger(__name__)


def _load_subject_ids() -> tuple[set[str], set[str]]:
    settings = get_settings_payload()
    install_subject_ids = {
        str(x)
        for x in (
            settings.get('installation_subject_ids')
            or settings.get('subject_groups', {}).get('instalacao')
            or sorted(DEFAULT_INSTALL_ASSUNTOS)
        )
    }
    maintenance_subject_ids = {
        str(x)
        for x in (
            settings.get('maintenance_subject_ids')
            or settings.get('subject_groups', {}).get('manutencao')
            or sorted(DEFAULT_MAINTENANCE_ASSUNTOS)
        )
    }
    return install_subject_ids, maintenance_subject_ids


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
    install_subject_ids, maintenance_subject_ids = _load_subject_ids()

    d = dict(definition_json or {})
    category = d.get('category')
    if category == 'instalacao':
        d['assunto_ids'] = sorted(install_subject_ids)
    elif category == 'manutencao':
        d['assunto_ids'] = sorted(maintenance_subject_ids)

    if not d.get('status_codes'):
        if scope == 'agenda_week':
            d['status_codes'] = STATUS_GROUPS['scheduled']
        else:
            merged = STATUS_GROUPS['open_like'] + STATUS_GROUPS['scheduled']
            d['status_codes'] = sorted(set(merged))

    if scope == 'maintenances' and not d.get('assunto_ids'):
        d['assunto_ids'] = sorted(maintenance_subject_ids)

    return d


def _infer_type(assunto_id: str, install_subject_ids: set[str], maintenance_subject_ids: set[str]) -> str:
    if assunto_id in install_subject_ids:
        return 'instalacao'
    if assunto_id in maintenance_subject_ids:
        return 'manutencao'
    return 'outros'


def _extract_customer_name(c: dict[str, Any]) -> str | None:
    return c.get('razao') or c.get('razao_social') or c.get('nome') or c.get('fantasia')


def normalize_row(
    row: dict[str, Any],
    customer: dict[str, Any] | None,
    install_subject_ids: set[str],
    maintenance_subject_ids: set[str],
) -> dict[str, Any]:
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
        'type': _infer_type(assunto_id, install_subject_ids, maintenance_subject_ids),
        'id_cliente': str(row.get('id_cliente') or ''),
        'id_filial': str(row.get('id_filial') or ''),
        'customer_name': _extract_customer_name(c),
        'phone': c.get('telefone') or c.get('whatsapp') or c.get('celular'),
        'address': row.get('endereco') or c.get('endereco'),
        'bairro': row.get('bairro') or c.get('bairro'),
        'cidade': c.get('cidade') or row.get('cidade'),
        'protocolo': str(row.get('protocolo') or ''),
        'source': 'ixc',
    }


def _build_grid_for_date_field(
    date_field: str,
    date_start: date,
    date_end: date,
    statuses: list[str],
    assunto_ids: list[str],
) -> list[list[dict[str, str]]]:
    base = [
        {'TB': date_field, 'OP': '>=', 'P': date_start.strftime('%Y-%m-%d 00:00:00')},
        {'TB': date_field, 'OP': '<=', 'P': date_end.strftime('%Y-%m-%d 23:59:59')},
    ]
    status_list = statuses or [None]
    assunto_list = assunto_ids or [None]
    grids: list[list[dict[str, str]]] = []
    for status in status_list:
        for assunto in assunto_list:
            grid = list(base)
            if status:
                grid.append({'TB': TB_OS_STATUS, 'OP': '=', 'P': status})
            if assunto:
                grid.append({'TB': TB_OS_ID_ASSUNTO, 'OP': '=', 'P': assunto})
            grids.append(grid)
    return grids


def _fetch_order_rows(
    adapter: IXCAdapter,
    date_start: date,
    date_end: date,
    statuses: list[str],
    assunto_ids: list[str],
    date_field: str = 'su_oss_chamado.data_agenda',
    filial_id: str | None = None,
) -> list[dict[str, Any]]:
    if date_field == 'su_oss_chamado.data_agenda':
        grids = expand_os_query_grids(date_start, date_end, statuses, assunto_ids, use_in=False)
    else:
        grids = _build_grid_for_date_field(date_field, date_start, date_end, statuses, assunto_ids)

    if filial_id:
        grids = [grid + [{'TB': TB_OS_ID_FILIAL, 'OP': '=', 'P': filial_id}] for grid in grids]

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for grid in grids:
        for row in adapter.list_service_orders(grid):
            key = str(row.get('id') or '')
            if key and key not in seen:
                seen.add(key)
                rows.append(row)
    return rows


def _fetch_order_rows_without_date(
    adapter: IXCAdapter,
    statuses: list[str],
    assunto_ids: list[str],
) -> list[dict[str, Any]]:
    status_list = statuses or [None]
    assunto_list = assunto_ids or [None]
    grids: list[list[dict[str, str]]] = []
    for status in status_list:
        for assunto in assunto_list:
            grid: list[dict[str, str]] = []
            if status:
                grid.append({'TB': TB_OS_STATUS, 'OP': '=', 'P': status})
            if assunto:
                grid.append({'TB': TB_OS_ID_ASSUNTO, 'OP': '=', 'P': assunto})
            grids.append(grid)

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for grid in grids:
        for row in adapter.list_service_orders(grid):
            key = str(row.get('id') or '')
            if key and key not in seen:
                seen.add(key)
                rows.append(row)
    return rows


def _sort_rows(rows: list[dict[str, Any]], field: str, reverse: bool = False) -> list[dict[str, Any]]:
    def key_fn(row: dict[str, Any]):
        dt = _parse_dt(row.get(field))
        if dt is None:
            return datetime.max if not reverse else datetime.min
        return dt

    return sorted(rows, key=key_fn, reverse=reverse)


def fetch_dashboard_items(
    adapter: IXCAdapter,
    scope: str,
    date_start: date,
    date_end: date,
    definition_json: dict[str, Any] | None,
    filial_id: str | None = None,
) -> list[dict[str, Any]]:
    install_subject_ids, maintenance_subject_ids = _load_subject_ids()
    definition = resolve_definition(definition_json, scope)
    statuses = [str(x) for x in definition.get('status_codes') or []]
    assunto_ids = [str(x) for x in definition.get('assunto_ids') or []]

    rows = _fetch_order_rows(adapter, date_start, date_end, statuses, assunto_ids, filial_id=filial_id)

    ids = sorted({str(r.get('id_cliente')) for r in rows if r.get('id_cliente')})
    clientes = adapter.list_clientes_by_ids(ids) if ids else {}

    return [
        normalize_row(r, clientes.get(str(r.get('id_cliente') or '')), install_subject_ids, maintenance_subject_ids)
        for r in rows
    ]


def _capacity_entry(limit: int, count: int) -> dict[str, Any]:
    safe_limit = max(0, int(limit))
    remaining = safe_limit - count
    fill_ratio = 1.0 if safe_limit <= 0 and count > 0 else (0.0 if safe_limit <= 0 else count / safe_limit)
    level = 'green'
    if remaining <= 0 or fill_ratio >= 1.0:
        level = 'red'
    elif fill_ratio >= 0.8 and remaining > 0:
        level = 'yellow'
    return {
        'limit': safe_limit,
        'count': count,
        'remaining': remaining,
        'fill_ratio': round(fill_ratio, 2),
        'level': level,
    }


def _build_day_capacity(counts: dict[str, int], day: date, agenda_capacity: dict[str, dict[str, int]], filial_id: str | None) -> dict[str, Any]:
    weekday_index = day.weekday()
    weekday = WEEKDAY_KEYS[weekday_index]
    limits = {
        '1': int((agenda_capacity.get('1') or {}).get(weekday, 0) or 0),
        '2': int((agenda_capacity.get('2') or {}).get(weekday, 0) or 0),
    }

    logger.info(
        'agenda_capacity day=%s weekday=%s selected_key=%s limit_f1=%s limit_f2=%s count_f1=%s count_f2=%s',
        day.strftime('%Y-%m-%d'),
        weekday_index,
        weekday,
        limits['1'],
        limits['2'],
        counts.get('1', 0),
        counts.get('2', 0),
    )

    if filial_id in ('1', '2'):
        entry = _capacity_entry(limits[filial_id], counts.get(filial_id, 0))
        return {'filial_1': entry if filial_id == '1' else _capacity_entry(0, 0), 'filial_2': entry if filial_id == '2' else _capacity_entry(0, 0), 'total': entry}

    filial_1 = _capacity_entry(limits['1'], counts.get('1', 0))
    filial_2 = _capacity_entry(limits['2'], counts.get('2', 0))
    return {
        'filial_1': filial_1,
        'filial_2': filial_2,
        'total': _capacity_entry(limits['1'] + limits['2'], counts.get('1', 0) + counts.get('2', 0)),
    }


def build_agenda_week(
    adapter: IXCAdapter,
    date_start: date,
    days: int,
    definition_json: dict[str, Any] | None,
    filial_id: str | None = None,
) -> dict[str, Any]:
    install_subject_ids, _ = _load_subject_ids()
    total_days = max(1, min(days, 31))
    date_end = date_start + timedelta(days=total_days - 1)
    items = fetch_dashboard_items(adapter, 'agenda_week', date_start, date_end, definition_json, filial_id=filial_id)
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        grouped.setdefault(item.get('date') or '', []).append(item)

    capacity_rows = _fetch_order_rows(
        adapter,
        date_start,
        date_end,
        CAPACITY_STATUS_CODES,
        sorted(install_subject_ids),
        date_field='su_oss_chamado.data_agenda',
        filial_id=filial_id,
    )
    counts_by_day: dict[str, dict[str, int]] = {}
    for row in capacity_rows:
        dt = _parse_dt(row.get('data_agenda'))
        if not dt:
            continue
        day_key = dt.strftime('%Y-%m-%d')
        row_filial = str(row.get('id_filial') or '')
        if row_filial not in ('1', '2'):
            continue
        counts_by_day.setdefault(day_key, {'1': 0, '2': 0})
        counts_by_day[day_key][row_filial] += 1

    settings = get_settings_payload()
    agenda_capacity = settings.get('agenda_capacity') or {}

    payload_days: list[dict[str, Any]] = []
    for idx in range(total_days):
        current = date_start + timedelta(days=idx)
        day_key = current.strftime('%Y-%m-%d')
        day_items = grouped.get(day_key, [])
        payload_days.append(
            {
                'date': day_key,
                'items': day_items,
                'capacity': _build_day_capacity(counts_by_day.get(day_key, {'1': 0, '2': 0}), current, agenda_capacity, filial_id),
            }
        )

    return {'days': payload_days}


def fetch_maintenance_items(
    adapter: IXCAdapter,
    definition_json: dict[str, Any] | None,
    tab: str = 'open',
    date_start: date | None = None,
    date_end: date | None = None,
) -> list[dict[str, Any]]:
    install_subject_ids, maintenance_subject_ids = _load_subject_ids()
    definition = resolve_definition(definition_json, 'maintenances')
    assunto_ids = [str(x) for x in (definition.get('assunto_ids') or sorted(maintenance_subject_ids))]
    statuses = MAINTENANCE_TAB_STATUS.get(tab, MAINTENANCE_TAB_STATUS['open'])

    selected_statuses = {str(s) for s in definition.get('status_codes') or []}
    if selected_statuses:
        statuses = [status for status in statuses if status in selected_statuses]

    if date_start and date_end:
        if tab == 'done':
            rows = _fetch_order_rows(adapter, date_start, date_end, statuses, assunto_ids, date_field='su_oss_chamado.data_fechamento')
        elif tab == 'open':
            rows = _fetch_order_rows(adapter, date_start, date_end, statuses, assunto_ids, date_field='su_oss_chamado.data_abertura')
        else:
            rows = _fetch_order_rows(adapter, date_start, date_end, statuses, assunto_ids, date_field='su_oss_chamado.data_agenda')
    else:
        rows = _fetch_order_rows_without_date(adapter, statuses, assunto_ids)

    if tab == 'done':
        rows = _sort_rows(rows, 'data_fechamento', reverse=True)
    elif tab == 'open':
        rows = _sort_rows(rows, 'data_abertura', reverse=False)

    ids = sorted({str(r.get('id_cliente')) for r in rows if r.get('id_cliente')})
    clientes = adapter.list_clientes_by_ids(ids) if ids else {}
    return [
        normalize_row(r, clientes.get(str(r.get('id_cliente') or '')), install_subject_ids, maintenance_subject_ids)
        for r in rows
    ]


def _resolve_today(today: str | None, tz_name: str | None) -> date:
    if today:
        return parse_date_or_default(today, date.today())

    if not tz_name:
        return date.today()

    try:
        return datetime.now(ZoneInfo(tz_name)).date()
    except ZoneInfoNotFoundError:
        return date.today()


def _is_same_day(raw: str | None, reference: date) -> bool:
    dt = _parse_dt(raw)
    if not dt:
        return False
    return dt.date() == reference


def _is_within_day_bounds(raw: str | None, day_start: datetime, day_end: datetime) -> bool:
    dt = _parse_dt(raw)
    if not dt:
        return False
    return day_start <= dt <= day_end


def _fetch_rows_for_exact_day(
    adapter: IXCAdapter,
    date_field: str,
    day: date,
    assunto_ids: list[str],
    filial_id: str | None = None,
) -> list[dict[str, Any]]:
    start = f"{day.strftime('%Y-%m-%d')} 00:00:00"
    next_day = day + timedelta(days=1)
    end = f"{next_day.strftime('%Y-%m-%d')} 00:00:00"

    assunto_list = assunto_ids or [None]
    grids: list[list[dict[str, str]]] = []
    for assunto in assunto_list:
        grid = [
            {'TB': date_field, 'OP': '>=', 'P': start},
            {'TB': date_field, 'OP': '<', 'P': end},
        ]
        if assunto:
            grid.append({'TB': TB_OS_ID_ASSUNTO, 'OP': '=', 'P': assunto})
        if filial_id:
            grid.append({'TB': TB_OS_ID_FILIAL, 'OP': '=', 'P': filial_id})
        grids.append(grid)

    seen: set[str] = set()
    rows: list[dict[str, Any]] = []
    for grid in grids:
        for row in adapter.list_service_orders(grid):
            key = str(row.get('id') or '')
            if key and key not in seen:
                seen.add(key)
                rows.append(row)
    return rows


def _count_by_day(rows: list[dict[str, Any]], field: str, date_start: date, total_days: int) -> list[dict[str, Any]]:
    counts = { (date_start + timedelta(days=idx)).strftime('%Y-%m-%d'): 0 for idx in range(total_days) }
    for row in rows:
        dt = _parse_dt(row.get(field))
        if not dt:
            continue
        key = dt.strftime('%Y-%m-%d')
        if key in counts:
            counts[key] += 1
    return [{'date': day, 'count': counts[day]} for day in sorted(counts.keys())]


def _status_filtered(rows: list[dict[str, Any]], definition_json: dict[str, Any] | None) -> list[dict[str, Any]]:
    definition = dict(definition_json or {})
    selected_statuses = {str(s) for s in definition.get('status_codes') or []}
    if not selected_statuses:
        return rows
    return [row for row in rows if str(row.get('status') or '') in selected_statuses]


def build_dashboard_summary(
    adapter: IXCAdapter,
    date_start: date,
    days: int,
    definition_json: dict[str, Any] | None,
    filial_id: str | None = None,
    today: str | None = None,
    tz_name: str | None = DEFAULT_SUMMARY_TZ,
) -> dict[str, Any]:
    install_subject_ids, maintenance_subject_ids = _load_subject_ids()
    total_days = max(1, min(days, 31))
    date_end = date_start + timedelta(days=total_days - 1)
    today_date = _resolve_today(today, tz_name)
    day_start = datetime.combine(today_date, datetime.min.time())
    day_end = datetime.combine(today_date, datetime.max.time().replace(microsecond=0))

    install_rows = _fetch_order_rows(
        adapter,
        date_start,
        date_end,
        STATUS_GROUPS['open_like'] + STATUS_GROUPS['scheduled'] + STATUS_GROUPS['done'],
        sorted(install_subject_ids),
        date_field='su_oss_chamado.data_agenda',
        filial_id=filial_id,
    )
    maint_period_rows = _fetch_order_rows(
        adapter,
        date_start,
        date_end,
        STATUS_GROUPS['open_like'] + STATUS_GROUPS['scheduled'] + STATUS_GROUPS['done'],
        sorted(maintenance_subject_ids),
        date_field='su_oss_chamado.data_abertura',
        filial_id=filial_id,
    )
    maint_open_rows = _fetch_order_rows(
        adapter,
        date_start,
        date_end,
        STATUS_GROUPS['open_like'],
        sorted(maintenance_subject_ids),
        date_field='su_oss_chamado.data_abertura',
        filial_id=filial_id,
    )
    maint_done_rows = _fetch_order_rows(
        adapter,
        date_start,
        date_end,
        STATUS_GROUPS['done'],
        sorted(maintenance_subject_ids),
        date_field='su_oss_chamado.data_fechamento',
        filial_id=filial_id,
    )
    maint_opened_today_rows = _fetch_rows_for_exact_day(
        adapter,
        date_field='su_oss_chamado.data_abertura',
        day=today_date,
        assunto_ids=sorted(maintenance_subject_ids),
        filial_id=filial_id,
    )

    install_rows = _status_filtered(install_rows, definition_json)
    maint_period_rows = _status_filtered(maint_period_rows, definition_json)
    maint_open_rows = _status_filtered(maint_open_rows, definition_json)
    maint_done_rows = _status_filtered(maint_done_rows, definition_json)

    return {
        'period': {'start': date_start.strftime('%Y-%m-%d'), 'end': date_end.strftime('%Y-%m-%d')},
        'instalacoes': {
            'agendadas_hoje': sum(
                1
                for row in install_rows
                if str(row.get('status') or '') in STATUS_GROUPS['scheduled'] and _is_same_day(row.get('data_agenda'), today_date)
            ),
            'finalizadas_hoje': sum(
                1
                for row in install_rows
                if str(row.get('status') or '') == 'F' and _is_same_day(row.get('data_fechamento'), today_date)
            ),
            'total_periodo': len(install_rows),
        },
        'manutencoes': {
            'abertas_total': len(maint_open_rows),
            'abertas_hoje': sum(
                1 for row in maint_opened_today_rows if _is_within_day_bounds(row.get('data_abertura'), day_start, day_end)
            ),
            'finalizadas_hoje': sum(
                1
                for row in maint_done_rows
                if str(row.get('status') or '') == 'F' and _is_same_day(row.get('data_fechamento'), today_date)
            ),
            'total_periodo': len(maint_period_rows),
        },
        'installations_scheduled_by_day': _count_by_day(install_rows, 'data_agenda', date_start, total_days),
        'maint_opened_by_day': _count_by_day(maint_open_rows, 'data_abertura', date_start, total_days),
        'maint_closed_by_day': _count_by_day(maint_done_rows, 'data_fechamento', date_start, total_days),
    }
