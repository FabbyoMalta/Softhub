import json

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_save_and_list_filters():
    payload = {
        'name': 'Filtro teste',
        'scope': 'agenda_week',
        'definition_json': {'types': ['manutencao'], 'status': ['agendada']},
    }
    created = client.post('/filters', json=payload)
    assert created.status_code == 201
    body = created.json()
    assert body['id']

    listed = client.get('/filters', params={'scope': 'agenda_week'})
    assert listed.status_code == 200
    assert any(item['id'] == body['id'] for item in listed.json())


def test_dashboard_agenda_week_returns_mock_data():
    response = client.get('/dashboard/agenda-week')
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert {'id', 'date', 'type'}.issubset(data[0].keys())


def test_dashboard_maintenances_uses_status_filtering():
    filt = {'status': ['agendada']}
    response = client.get('/dashboard/maintenances', params={'filter_json': json.dumps(filt)})
    assert response.status_code == 200
    data = response.json()
    assert len(data) > 0
    assert all(item['status'] == 'agendada' for item in data)
    assert all(item['type'] == 'manutencao' for item in data)
