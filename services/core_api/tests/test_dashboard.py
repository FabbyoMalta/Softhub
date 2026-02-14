from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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
