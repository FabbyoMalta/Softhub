from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.services import dashboard as dashboard_service
from app.services.adapters import get_ixc_adapter

client = TestClient(app)


class _SummaryAdapter:
    def __init__(self, rows):
        self.rows = rows

    def list_service_orders(self, grid_filters):
        field_map = {
            'su_oss_chamado.data_agenda': 'data_agenda',
            'su_oss_chamado.data_abertura': 'data_abertura',
            'su_oss_chamado.data_fechamento': 'data_fechamento',
            'su_oss_chamado.status': 'status',
            'su_oss_chamado.id_assunto': 'id_assunto',
            'su_oss_chamado.id_filial': 'id_filial',
        }

        def match(row, flt):
            tb, op, p = flt.get('TB'), flt.get('OP'), str(flt.get('P') or '')
            value = str(row.get(field_map.get(tb, ''), '') or '')
            if op == '=':
                return value == p
            if op == 'IN':
                return value in [x.strip() for x in p.split(',') if x.strip()]
            if op == '>=':
                return value >= p
            if op == '<=':
                return value <= p
            if op == '<':
                return value < p
            return True

        out = self.rows
        for f in grid_filters:
            out = [row for row in out if match(row, f)]
        return out

    def list_clientes_by_ids(self, ids):
        return {}


def test_saved_filters_crud_and_list():
    payload = {
        'name': 'Filtro manutenção',
        'scope': 'maintenances',
        'definition_json': {'status_codes': ['AG', 'RAG'], 'assunto_ids': ['17', '31']},
    }
    created = client.post('/filters', json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body['id']

    listed = client.get('/filters', params={'scope': 'maintenances'})
    assert listed.status_code == 200
    assert any(item['id'] == body['id'] for item in listed.json())


def test_dashboard_agenda_week_returns_mock_data():
    response = client.get('/dashboard/agenda-week')
    assert response.status_code == 200
    data = response.json()
    assert 'days' in data
    assert len(data['days']) > 0
    assert {'date', 'items', 'capacity'}.issubset(data['days'][0].keys())


def test_dashboard_enrichment_customer_name():
    response = client.get('/dashboard/agenda-week')
    assert response.status_code == 200
    days = response.json()['days']
    items = [item for day in days for item in day['items']]
    assert any(item.get('customer_name') for item in items)


def test_saved_filters_update():
    created = client.post(
        '/filters',
        json={
            'name': 'Filtro inicial',
            'scope': 'maintenances',
            'definition_json': {'status_codes': ['AG']},
        },
    )
    assert created.status_code == 201
    filter_id = created.json()['id']

    updated = client.put(
        f'/filters/{filter_id}',
        json={
            'name': 'Filtro atualizado',
            'scope': 'maintenances',
            'definition_json': {'status_codes': ['RAG'], 'assunto_ids': ['17']},
        },
    )
    assert updated.status_code == 200
    assert updated.json()['name'] == 'Filtro atualizado'
    assert updated.json()['definition_json'] == {'status_codes': ['RAG'], 'assunto_ids': ['17']}


def test_dashboard_summary_returns_expected_shape():
    response = client.get('/dashboard/summary', params={'start': '2025-01-01', 'days': 7, 'today': '2025-01-02'})
    assert response.status_code == 200
    data = response.json()
    assert data['period']['start'] == '2025-01-01'
    assert data['period']['end'] == '2025-01-07'
    assert set(data['instalacoes'].keys()) == {'agendadas_hoje', 'finalizadas_hoje', 'total_periodo'}
    assert set(data['manutencoes'].keys()) == {'abertas_total', 'abertas_hoje', 'finalizadas_hoje', 'total_periodo'}
    assert 'installations_scheduled_by_day' in data
    assert 'maint_opened_by_day' in data
    assert 'maint_closed_by_day' in data


def test_settings_get_and_put():
    get_response = client.get('/settings')
    assert get_response.status_code == 200
    payload = get_response.json()
    payload['subject_groups']['outros'] = ['99']
    payload['agenda_capacity']['1']['mon'] = 8
    payload['filiais']['1'] = 'GV'

    update_response = client.put('/settings', json=payload)
    assert update_response.status_code == 200
    data = update_response.json()
    assert data['subject_groups']['outros'] == ['99']
    assert data['agenda_capacity']['1']['mon'] == 8
    assert data['filiais']['1'] == 'GV'
    assert {'1', '15'} == set(data['installation_subject_ids'])
    assert {'17', '34', '31'} == set(data['maintenance_subject_ids'])


def test_dashboard_summary_uses_correct_date_fields_per_type():
    rows = [
        {'id': 'I-1', 'id_assunto': '15', 'status': 'AG', 'data_agenda': '2025-01-02 10:00:00', 'data_abertura': '2025-01-01 09:00:00', 'data_fechamento': None},
        {'id': 'I-2', 'id_assunto': '1', 'status': 'F', 'data_agenda': '2025-01-01 10:00:00', 'data_abertura': '2025-01-01 09:00:00', 'data_fechamento': '2025-01-02 11:00:00'},
        {'id': 'M-1', 'id_assunto': '17', 'status': 'A', 'data_agenda': '2025-01-01 09:00:00', 'data_abertura': '2025-01-02 08:00:00', 'data_fechamento': None},
        {'id': 'M-2', 'id_assunto': '31', 'status': 'F', 'data_agenda': '2025-01-01 09:00:00', 'data_abertura': '2024-12-31 08:00:00', 'data_fechamento': '2025-01-02 12:00:00'},
    ]

    summary = dashboard_service.build_dashboard_summary(_SummaryAdapter(rows), date(2025, 1, 1), 7, {}, today='2025-01-02', tz_name='America/Sao_Paulo')

    assert summary['instalacoes']['agendadas_hoje'] == 1
    assert summary['instalacoes']['finalizadas_hoje'] == 1
    assert summary['instalacoes']['total_periodo'] == 2
    assert summary['manutencoes']['abertas_total'] == 1
    assert summary['manutencoes']['abertas_hoje'] == 1
    assert summary['manutencoes']['finalizadas_hoje'] == 1
    assert summary['manutencoes']['total_periodo'] == 1


def test_dashboard_summary_opened_today_uses_data_abertura_and_ignores_status():
    rows = [
        {'id': 'M-1', 'id_assunto': '17', 'status': 'A', 'data_agenda': '2025-01-02 09:00:00', 'data_abertura': '2025-01-01 08:00:00', 'data_fechamento': None},
        {'id': 'M-2', 'id_assunto': '17', 'status': 'A', 'data_agenda': '2025-01-01 09:00:00', 'data_abertura': '2025-01-02 08:00:00', 'data_fechamento': None},
        {'id': 'M-3', 'id_assunto': '17', 'status': 'F', 'data_agenda': '2025-01-02 09:00:00', 'data_abertura': '2025-01-02 11:00:00', 'data_fechamento': '2025-01-02 12:00:00'},
    ]

    summary = dashboard_service.build_dashboard_summary(_SummaryAdapter(rows), date(2025, 1, 1), 7, {}, today='2025-01-02', tz_name='America/Sao_Paulo')
    assert summary['manutencoes']['abertas_hoje'] == 2


def test_dashboard_summary_fallbacks_to_server_local_date_when_tz_missing():
    summary = dashboard_service.build_dashboard_summary(_SummaryAdapter([]), date(2025, 1, 1), 7, {}, today='2025-01-02', tz_name=None)
    assert summary['period']['start'] == '2025-01-01'


class _QueueMaintenanceAdapter:
    def list_service_orders(self, grid_filters):
        row = {
            'id': 'M-QUEUE-1',
            'id_cliente': '900',
            'id_assunto': '17',
            'status': 'A',
            'data_agenda': None,
            'data_abertura': '2025-01-03 10:00:00',
            'data_fechamento': None,
            'bairro': 'Centro',
            'endereco': 'Rua Teste',
            'protocolo': 'PX-1',
            'id_filial': '1',
        }
        field_map = {
            'su_oss_chamado.status': 'status',
            'su_oss_chamado.id_assunto': 'id_assunto',
            'su_oss_chamado.data_abertura': 'data_abertura',
            'su_oss_chamado.data_agenda': 'data_agenda',
            'su_oss_chamado.data_fechamento': 'data_fechamento',
            'su_oss_chamado.id_filial': 'id_filial',
        }

        def match(flt):
            tb, op, p = flt.get('TB'), flt.get('OP'), str(flt.get('P') or '')
            value = str(row.get(field_map.get(tb, ''), '') or '')
            if op == '=':
                return value == p
            if op == 'IN':
                return value in [x.strip() for x in p.split(',') if x.strip()]
            if op == '>=':
                return value >= p
            if op == '<=':
                return value <= p
            return True

        return [row] if all(match(f) for f in grid_filters) else []

    def list_clientes_by_ids(self, ids):
        return {'900': {'nome': 'Cliente Fila', 'bairro': 'Centro', 'cidade': 'Vitória'}}


def test_maintenances_queue_mode_returns_open_without_data_agenda():
    app.dependency_overrides[get_ixc_adapter] = lambda: _QueueMaintenanceAdapter()
    try:
        response = client.get('/dashboard/maintenances', params={'tab': 'open'})
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]['id'] == 'M-QUEUE-1'
    finally:
        app.dependency_overrides.pop(get_ixc_adapter, None)


def test_agenda_capacity_by_filial_and_total():
    rows = [
        {'id': 'I-1', 'id_cliente': '1', 'id_assunto': '1', 'status': 'AG', 'data_agenda': '2026-02-16 09:00:00', 'id_filial': '1'},
        {'id': 'I-2', 'id_cliente': '2', 'id_assunto': '1', 'status': 'AG', 'data_agenda': '2026-02-16 10:00:00', 'id_filial': '1'},
        {'id': 'I-3', 'id_cliente': '3', 'id_assunto': '1', 'status': 'AG', 'data_agenda': '2026-02-16 11:00:00', 'id_filial': '2'},
    ]
    agenda = dashboard_service.build_agenda_week(_SummaryAdapter(rows), date(2026, 2, 16), 1, {}, filial_id=None)
    day = agenda['days'][0]
    assert day['capacity']['filial_1']['count'] == 2
    assert day['capacity']['filial_2']['count'] == 1
    assert day['capacity']['total']['count'] == 3
    assert day['capacity']['filial_1']['remaining'] == day['capacity']['filial_1']['limit'] - 2


def test_agenda_capacity_filters_single_filial():
    rows = [
        {'id': 'I-1', 'id_cliente': '1', 'id_assunto': '1', 'status': 'AG', 'data_agenda': '2026-02-16 09:00:00', 'id_filial': '1'},
        {'id': 'I-2', 'id_cliente': '2', 'id_assunto': '1', 'status': 'AG', 'data_agenda': '2026-02-16 10:00:00', 'id_filial': '2'},
    ]
    agenda = dashboard_service.build_agenda_week(_SummaryAdapter(rows), date(2026, 2, 16), 1, {}, filial_id='2')
    day = agenda['days'][0]
    assert len(day['items']) == 1
    assert day['items'][0]['id_filial'] == '2'
    assert day['capacity']['total']['count'] == 1


def test_agenda_capacity_includes_finalized_status_f_for_slot_count():
    rows = [
        {'id': 'I-1', 'id_cliente': '1', 'id_assunto': '1', 'status': 'F', 'data_agenda': '2026-02-17 09:00:00', 'id_filial': '1'},
        {'id': 'I-2', 'id_cliente': '2', 'id_assunto': '1', 'status': 'AG', 'data_agenda': '2026-02-17 10:00:00', 'id_filial': '1'},
    ]
    agenda = dashboard_service.build_agenda_week(_SummaryAdapter(rows), date(2026, 2, 17), 1, {}, filial_id='1')
    day = agenda['days'][0]
    assert day['capacity']['total']['count'] == 2


def test_agenda_capacity_uses_tue_limit_mapping():
    rows = [
        {'id': 'I-1', 'id_cliente': '1', 'id_assunto': '1', 'status': 'AG', 'data_agenda': '2026-02-17 09:00:00', 'id_filial': '1'},
        {'id': 'I-2', 'id_cliente': '2', 'id_assunto': '1', 'status': 'AG', 'data_agenda': '2026-02-17 10:00:00', 'id_filial': '1'},
        {'id': 'I-3', 'id_cliente': '3', 'id_assunto': '1', 'status': 'AG', 'data_agenda': '2026-02-17 11:00:00', 'id_filial': '1'},
        {'id': 'I-4', 'id_cliente': '4', 'id_assunto': '1', 'status': 'AG', 'data_agenda': '2026-02-17 12:00:00', 'id_filial': '1'},
        {'id': 'I-5', 'id_cliente': '5', 'id_assunto': '1', 'status': 'AG', 'data_agenda': '2026-02-17 13:00:00', 'id_filial': '1'},
        {'id': 'I-6', 'id_cliente': '6', 'id_assunto': '1', 'status': 'AG', 'data_agenda': '2026-02-17 14:00:00', 'id_filial': '1'},
    ]
    agenda = dashboard_service.build_agenda_week(_SummaryAdapter(rows), date(2026, 2, 17), 1, {}, filial_id='1')
    day = agenda['days'][0]
    assert day['capacity']['total']['limit'] == 5
    assert day['capacity']['total']['count'] == 6
    assert day['capacity']['total']['level'] == 'red'
