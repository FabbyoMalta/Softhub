from fastapi.testclient import TestClient

from app.adapters.ixc_adapter import MockIXCAdapter
from app.main import app
from app.services.adapters import get_ixc_adapter
from app.services.billing import build_billing_open_response


def test_billing_open_summary_and_contract_enrich():
    data = build_billing_open_response(MockIXCAdapter())
    assert data['summary']['total_open'] == 2
    assert data['summary']['over_20_days'] >= 1
    assert data['items'][0]['contract']['id'] == '2'


def test_billing_open_sets_cache_header(monkeypatch):
    payload = {
        'summary': {'total_open': 0, 'over_20_days': 0, 'oldest_due_date': None},
        'items': [],
    }

    monkeypatch.setattr('app.api.billing.cache_get_json', lambda key: None)
    monkeypatch.setattr('app.api.billing.cache_set_json', lambda key, value, ttl_s=60: None)
    monkeypatch.setattr('app.api.billing.build_billing_open_response', lambda adapter: payload)

    response = TestClient(app).get('/billing/open')
    assert response.status_code == 200
    assert response.headers.get('X-Cache') == 'MISS'
    assert response.json() == payload


def test_billing_open_endpoint_with_mock_adapter(monkeypatch):
    monkeypatch.setattr('app.api.billing.cache_get_json', lambda key: None)
    monkeypatch.setattr('app.api.billing.cache_set_json', lambda key, value, ttl_s=60: None)

    app.dependency_overrides[get_ixc_adapter] = lambda: MockIXCAdapter()
    try:
        response = TestClient(app).get('/billing/open')
    finally:
        app.dependency_overrides.pop(get_ixc_adapter, None)

    assert response.status_code == 200
    payload = response.json()
    assert 'summary' in payload
    assert 'items' in payload
    assert payload['summary']['total_open'] == len(payload['items'])
