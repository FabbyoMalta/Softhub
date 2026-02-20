from fastapi.testclient import TestClient

from app.main import app
from app.services.adapters import get_ixc_adapter

client = TestClient(app)


class _MessagesAdapter:
    def list_oss_mensagens(self, id_chamado: str):
        return [
            {'id': '2', 'id_chamado': id_chamado, 'data': '2025-01-02 10:00:00', 'mensagem': 'Finalizada', 'id_evento': '99', 'status': 'F'},
            {'id': '1', 'id_chamado': id_chamado, 'data': '2025-01-02 08:00:00', 'mensagem': 'Criada', 'id_evento': '10', 'status': 'A'},
        ]


class _MessagesErrorAdapter:
    def list_oss_mensagens(self, id_chamado: str):
        return []


def test_get_oss_mensagens_returns_records_sorted_by_data():
    app.dependency_overrides[get_ixc_adapter] = lambda: _MessagesAdapter()
    try:
        response = client.get('/oss/9083/mensagens')
    finally:
        app.dependency_overrides.pop(get_ixc_adapter, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload['total'] == 2
    registros = payload['registros']
    ordered = sorted(registros, key=lambda r: r['data'])
    assert registros == ordered


def test_get_oss_mensagens_error_returns_empty_list_and_logs(caplog):
    app.dependency_overrides[get_ixc_adapter] = lambda: _MessagesErrorAdapter()
    try:
        response = client.get('/oss/9083/mensagens')
    finally:
        app.dependency_overrides.pop(get_ixc_adapter, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload['total'] == 0
    assert payload['registros'] == []


def test_real_adapter_logs_and_returns_empty_on_ixc_error(caplog):
    from app.adapters.ixc_adapter import RealIXCAdapter
    from app.clients.ixc_client import IXCClientError

    class _BrokenClient:
        def iterate_all(self, *args, **kwargs):
            raise IXCClientError('non-json response')

    adapter = RealIXCAdapter(_BrokenClient())
    with caplog.at_level('WARNING'):
        registros = adapter.list_oss_mensagens('9083')

    assert registros == []
    assert any('list_oss_mensagens failed' in rec.message for rec in caplog.records)
