from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import BillingCase, SessionLocal
from app.main import app
from app.services.adapters import get_ixc_adapter


class _BillingFlowAdapter:
    def list_contas_receber_para_sync(self, due_from, only_open=True, filial_id=None, rp=500, limit_pages=5):
        today = date.today()
        return [
            {
                'id': 'SYNC-30D',
                'id_cliente': '100',
                'filial_id': '1',
                'data_vencimento': (today - timedelta(days=30)).strftime('%Y-%m-%d'),
                'valor_aberto': '120.50',
                'tipo_recebimento': 'PIX',
                'id_contrato': '2',
            },
            {
                'id': 'SYNC-10D',
                'id_cliente': '101',
                'filial_id': '2',
                'data_vencimento': (today - timedelta(days=10)).strftime('%Y-%m-%d'),
                'valor_aberto': '44.90',
                'tipo_recebimento': 'BOLETO',
                'id_contrato_avulso': '3',
            },
            {
                'id': 'SYNC-ZERO',
                'id_cliente': '102',
                'filial_id': '2',
                'data_vencimento': (today - timedelta(days=35)).strftime('%Y-%m-%d'),
                'valor_aberto': '0',
                'tipo_recebimento': 'BOLETO',
            },
        ]

    def list_contratos_by_ids(self, ids: list[str]):
        data = {
            '2': {
                'id': '2',
                'status': 'A',
                'status_internet': 'A',
                'situacao_financeira_contrato': 'N',
                'pago_ate_data': '2026-01-01',
                'id_vendedor': '12',
                'contrato': 'Plano 600',
                'data_ativacao': '2024-01-01',
            },
            '3': {
                'id': '3',
                'status': 'A',
                'status_internet': 'CM',
                'situacao_financeira_contrato': 'R',
                'pago_ate_data': '2025-01-01',
                'id_vendedor': '10',
                'contrato': 'Plano 300',
                'data_ativacao': '2023-05-01',
            },
        }
        return [data[i] for i in ids if i in data]

    def list_clientes_by_ids(self, ids: list[str]):
        return [
            {
                'id': i,
                'nome': f'Cliente {i}',
                'telefone': '27999990000',
                'endereco': 'Rua A',
                'bairro': 'Centro',
                'cidade': 'Vitória',
            }
            for i in ids
        ]

    def create_billing_ticket(self, payload):
        return {'ticket_id': f"TICKET-{payload['external_id']}"}

    def close_billing_ticket(self, ticket_id: str, payload=None):
        return {'ticket_id': ticket_id, 'status': 'CLOSED'}

    def list_contas_receber_by_ids(self, external_ids: list[str]):
        # simula título pago ao desaparecer/zerar
        out = []
        for external_id in external_ids:
            if external_id == 'SYNC-PAID':
                out.append({'id': external_id, 'valor_aberto': '0'})
            else:
                out.append({'id': external_id, 'valor_aberto': '120.50'})
        return out


def _seed_cases() -> None:
    now = datetime.utcnow()
    with SessionLocal() as db:
        db.query(BillingCase).delete()
        db.add_all(
            [
                BillingCase(
                    external_id='CASE-1',
                    id_cliente='CLI-1',
                    id_contrato='CON-1',
                    filial_id='A',
                    due_date=date(2024, 1, 1),
                    amount_open=Decimal('100.00'),
                    open_days=10,
                    payment_type='BOLETO',
                    status_case='OPEN',
                    first_seen_at=now,
                    last_seen_at=now,
                    action_state='NONE',
                ),
                BillingCase(
                    external_id='CASE-2',
                    id_cliente='CLI-2',
                    id_contrato='CON-2',
                    filial_id='B',
                    due_date=date(2023, 12, 20),
                    amount_open=Decimal('230.50'),
                    open_days=25,
                    payment_type='PIX',
                    status_case='OPEN',
                    first_seen_at=now,
                    last_seen_at=now,
                    action_state='NOTIFIED',
                ),
                BillingCase(
                    external_id='CASE-3',
                    id_cliente='CLI-3',
                    filial_id='A',
                    due_date=date(2024, 2, 1),
                    amount_open=Decimal('0'),
                    open_days=0,
                    payment_type='CARTAO',
                    status_case='RESOLVED',
                    first_seen_at=now,
                    last_seen_at=now,
                    action_state='NONE',
                ),
                BillingCase(
                    external_id='CASE-4',
                    id_cliente='CLI-4',
                    filial_id='A',
                    due_date=date(2023, 12, 15),
                    amount_open=Decimal('50.00'),
                    open_days=31,
                    payment_type='BOLETO',
                    status_case='OPEN',
                    first_seen_at=now,
                    last_seen_at=now,
                    action_state='TICKET_OPENED',
                    ticket_id='EXISTING',
                    ticket_status='OPEN',
                ),
                BillingCase(
                    external_id='SYNC-PAID',
                    id_cliente='100',
                    filial_id='1',
                    due_date=date.today() - timedelta(days=31),
                    amount_open=Decimal('10.00'),
                    open_days=31,
                    payment_type='PIX',
                    status_case='OPEN',
                    first_seen_at=now,
                    last_seen_at=now,
                    action_state='TICKET_OPENED',
                    ticket_id='TICKET-SYNC-PAID',
                    ticket_status='OPEN',
                ),
            ]
        )
        db.commit()


def test_get_billing_cases_returns_open_items():
    _seed_cases()

    response = TestClient(app).get('/billing/cases/db')

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 4
    assert all(item['status_case'] == 'OPEN' for item in payload)


def test_get_billing_cases_filters_by_status_and_min_days():
    _seed_cases()

    response = TestClient(app).get('/billing/cases/db?status=OPEN&min_days=20')

    assert response.status_code == 200
    payload = response.json()
    assert {item['external_id'] for item in payload} >= {'CASE-2', 'CASE-4'}


def test_get_billing_cases_summary_matches_listing_count():
    _seed_cases()
    client = TestClient(app)

    listing = client.get('/billing/cases/db?status=OPEN&min_days=20')
    summary = client.get('/billing/cases/summary?status=OPEN&min_days=20')

    assert listing.status_code == 200
    assert summary.status_code == 200
    assert summary.json()['total_cases'] == len(listing.json())


def test_sync_and_enrich_and_ticket_flow(monkeypatch):
    _seed_cases()
    client = TestClient(app)
    monkeypatch.setenv('BILLING_TICKET_ENABLE', 'true')
    monkeypatch.setenv('BILLING_TICKET_ENDPOINT', 'su_ticket')
    monkeypatch.setenv('BILLING_TICKET_CLOSE_ENDPOINT', 'su_ticket')
    monkeypatch.setenv('BILLING_TICKET_SETOR_ID', '1')
    monkeypatch.setenv('BILLING_TICKET_ASSUNTO_ID', '2')
    get_settings.cache_clear()

    app.dependency_overrides[get_ixc_adapter] = lambda: _BillingFlowAdapter()
    try:
        sync_response = client.post('/billing/sync?due_from=2024-01-01&only_open=true&limit_pages=2&rp=200')
        assert sync_response.status_code == 200
        assert sync_response.json()['upserted'] >= 1

        enrich_response = client.post('/billing/enrich?limit=2000&only_missing=true')
        assert enrich_response.status_code == 200
        assert enrich_response.json()['updated'] >= 1

        cases = client.get('/billing/cases/db?status=OPEN&min_days=20').json()
        synced = next(item for item in cases if item['external_id'] == 'SYNC-30D')
        assert synced['contract_json'] is not None
        assert synced['client_json'] is not None

        dry = client.post(f"/billing/cases/{synced['id']}/ticket/dry-run")
        assert dry.status_code == 200
        assert dry.json()['payload'] is not None

        create = client.post(f"/billing/cases/{synced['id']}/ticket")
        assert create.status_code == 200
        assert create.json()['already_created'] is False

        create_again = client.post(f"/billing/cases/{synced['id']}/ticket")
        assert create_again.status_code == 200
        assert create_again.json()['already_created'] is True

        batch_dry = client.post('/billing/tickets/batch/dry-run', json={'filters': {'status': 'OPEN', 'min_days': 20}, 'limit': 100})
        assert batch_dry.status_code == 200

        batch = client.post('/billing/tickets/batch', json={'filters': {'status': 'OPEN', 'min_days': 20}, 'limit': 100, 'require_confirm': True})
        assert batch.status_code == 200
        assert batch.json()['created'] >= 0
    finally:
        app.dependency_overrides.pop(get_ixc_adapter, None)
        get_settings.cache_clear()


def test_reconcile_ready_to_close_when_disabled(monkeypatch):
    _seed_cases()
    client = TestClient(app)
    monkeypatch.setenv('BILLING_AUTOCLOSE_ENABLED', 'false')
    get_settings.cache_clear()

    app.dependency_overrides[get_ixc_adapter] = lambda: _BillingFlowAdapter()
    try:
        response = client.post('/billing/tickets/reconcile?limit=1000')
    finally:
        app.dependency_overrides.pop(get_ixc_adapter, None)
        get_settings.cache_clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload['closed'] == 0
    assert payload['would_close'] >= 1

    cases = client.get('/billing/cases/db?status=OPEN').json()
    paid_case = next(item for item in cases if item['external_id'] == 'SYNC-PAID')
    assert paid_case['action_state'] == 'READY_TO_CLOSE'



def test_get_billing_summary_endpoint():
    _seed_cases()
    client = TestClient(app)
    response = client.get('/billing/summary?status=open&only_over_20_days=true')
    assert response.status_code == 200
    payload = response.json()
    assert 'total_open' in payload
    assert 'over_20' in payload
    assert 'amount_open_sum' in payload



def test_reconcile_closes_when_enabled(monkeypatch):
    _seed_cases()
    client = TestClient(app)
    monkeypatch.setenv('BILLING_TICKET_ENABLE', 'true')
    monkeypatch.setenv('BILLING_TICKET_SETOR_ID', '1')
    monkeypatch.setenv('BILLING_TICKET_ASSUNTO_ID', '2')
    monkeypatch.setenv('BILLING_AUTOCLOSE_ENABLED', 'true')
    get_settings.cache_clear()

    app.dependency_overrides[get_ixc_adapter] = lambda: _BillingFlowAdapter()
    try:
        response = client.post('/billing/cases/reconcile?limit=1000')
    finally:
        app.dependency_overrides.pop(get_ixc_adapter, None)
        get_settings.cache_clear()

    assert response.status_code == 200
    payload = response.json()
    assert payload['closed'] >= 1



class _GroupedAdapter:
    def list_contas_receber_atrasadas(self, min_days: int = 20, due_from=None, due_to=None, filial_id=None):
        return [
            {'id': 'T1', 'id_cliente': '100', 'id_contrato': '2', 'id_contrato_avulso': '0', 'data_vencimento': '2024-01-10', 'data_emissao': '2023-12-10', 'valor_aberto': '100', 'valor': '100', 'tipo_recebimento': 'PIX', 'status': 'A'},
            {'id': 'T2', 'id_cliente': '100', 'id_contrato': '0', 'id_contrato_avulso': '3', 'data_vencimento': '2024-01-05', 'data_emissao': '2023-12-05', 'valor_aberto': '50', 'valor': '50', 'tipo_recebimento': 'BOL', 'status': 'A'},
            {'id': 'T3', 'id_cliente': '100', 'id_contrato': '2', 'id_contrato_avulso': '0', 'data_vencimento': '2024-01-01', 'data_emissao': '2023-12-01', 'valor_aberto': '30', 'valor': '30', 'tipo_recebimento': 'PIX', 'status': 'A'},
        ]

    def list_contas_receber_para_sync(self, due_from, only_open=True, filial_id=None, rp=500, limit_pages=5):
        return self.list_contas_receber_atrasadas()

    def list_clientes_by_ids(self, ids):
        return [{'id': i, 'nome': f'Cliente {i}'} for i in ids]


def test_grouped_cases_by_contract():
    client = TestClient(app)
    app.dependency_overrides[get_ixc_adapter] = lambda: _GroupedAdapter()
    try:
        response = client.get('/billing/cases?only_20p=true&group_by=contract&limit=500')
    finally:
        app.dependency_overrides.pop(get_ixc_adapter, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload['summary']['cases_total'] == 2
    keys = {c['case_key'] for c in payload['cases']}
    assert 'cliente:100|contrato:2' in keys
    assert 'cliente:100|contrato:3' in keys
    c2 = next(c for c in payload['cases'] if c['id_contrato'] == '2')
    assert [t['external_id'] for t in c2['titles']] == ['T3', 'T1']


def test_grouped_cases_by_client():
    client = TestClient(app)
    app.dependency_overrides[get_ixc_adapter] = lambda: _GroupedAdapter()
    try:
        response = client.get('/billing/cases?only_20p=true&group_by=client&limit=500')
    finally:
        app.dependency_overrides.pop(get_ixc_adapter, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload['summary']['cases_total'] == 1
    case = payload['cases'][0]
    assert case['id_cliente'] == '100'
    assert case['qtd_titulos'] == 3
