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
