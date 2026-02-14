from datetime import date

from fastapi.testclient import TestClient

from app.main import app
from app.services import dashboard as dashboard_service

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
    assert len(data) > 0
    assert {'id', 'date', 'status_code', 'status_label', 'type'}.issubset(data[0].keys())


def test_dashboard_enrichment_customer_name():
    response = client.get('/dashboard/agenda-week')
    assert response.status_code == 200
    data = response.json()
    assert any(item.get('customer_name') for item in data)


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

    listed = client.get('/filters', params={'scope': 'maintenances'})
    assert listed.status_code == 200
    item = next(filter_item for filter_item in listed.json() if filter_item['id'] == filter_id)
    assert item['name'] == 'Filtro atualizado'
    assert item['definition_json'] == {'status_codes': ['RAG'], 'assunto_ids': ['17']}


def test_dashboard_summary_returns_expected_shape():
    response = client.get('/dashboard/summary', params={'start': '2025-01-01', 'days': 7, 'today': '2025-01-02'})
    assert response.status_code == 200
    data = response.json()
    assert data['period']['start'] == '2025-01-01'
    assert data['period']['end'] == '2025-01-07'
    assert set(data['instalacoes'].keys()) == {'agendadas_hoje', 'finalizadas_hoje', 'total_periodo'}
    assert set(data['manutencoes'].keys()) == {'abertas_total', 'abertas_hoje', 'finalizadas_hoje', 'total_periodo'}


def test_settings_get_and_put():
    get_response = client.get('/settings')
    assert get_response.status_code == 200
    payload = get_response.json()
    payload['subject_groups']['outros'] = ['99']
    payload['default_filters']['agenda'] = None

    update_response = client.put('/settings', json=payload)
    assert update_response.status_code == 200
    assert update_response.json()['subject_groups']['outros'] == ['99']


def test_dashboard_summary_uses_correct_date_fields_per_type():
    rows = [
        {
            'id': 'I-1',
            'id_assunto': '1',
            'status': 'AG',
            'data_agenda': '2025-01-02 10:00:00',
            'data_abertura': '2025-01-01 09:00:00',
            'data_fechamento': None,
        },
        {
            'id': 'I-2',
            'id_assunto': '1',
            'status': 'F',
            'data_agenda': '2025-01-01 10:00:00',
            'data_abertura': '2025-01-01 09:00:00',
            'data_fechamento': '2025-01-02 11:00:00',
        },
        {
            'id': 'M-1',
            'id_assunto': '17',
            'status': 'A',
            'data_agenda': '2025-01-02 09:00:00',
            'data_abertura': '2025-01-02 08:00:00',
            'data_fechamento': None,
        },
        {
            'id': 'M-2',
            'id_assunto': '31',
            'status': 'F',
            'data_agenda': '2025-01-01 09:00:00',
            'data_abertura': '2024-12-31 08:00:00',
            'data_fechamento': '2025-01-02 12:00:00',
        },
    ]

    summary = dashboard_service.build_dashboard_summary(
        _SummaryAdapter(rows),
        date(2025, 1, 1),
        7,
        {},
        today='2025-01-02',
        tz_name='America/Sao_Paulo',
    )

    assert summary['instalacoes']['agendadas_hoje'] == 1
    assert summary['instalacoes']['finalizadas_hoje'] == 1
    assert summary['instalacoes']['total_periodo'] == 2

    assert summary['manutencoes']['abertas_total'] == 1
    assert summary['manutencoes']['abertas_hoje'] == 1
    assert summary['manutencoes']['finalizadas_hoje'] == 1
    assert summary['manutencoes']['total_periodo'] == 2


def test_dashboard_summary_fallbacks_to_server_local_date_when_tz_missing():
    summary = dashboard_service.build_dashboard_summary(
        _SummaryAdapter([]),
        date(2025, 1, 1),
        7,
        {},
        today='2025-01-02',
        tz_name=None,
    )
    assert summary['period']['start'] == '2025-01-01'
