from datetime import date, datetime, timedelta
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import BillingCase, SessionLocal
from app.main import app
from app.services.adapters import get_ixc_adapter


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
                ),
            ]
        )
        db.commit()


def test_get_billing_cases_returns_open_items():
    _seed_cases()

    response = TestClient(app).get('/billing/cases')

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 3
    assert all(item['status_case'] == 'OPEN' for item in payload)


def test_get_billing_cases_filters_by_status_and_min_days():
    _seed_cases()

    response = TestClient(app).get('/billing/cases?status=OPEN&min_days=20')

    assert response.status_code == 200
    payload = response.json()
    assert {item['external_id'] for item in payload} == {'CASE-2', 'CASE-4'}


def test_get_billing_cases_summary_matches_listing_count():
    _seed_cases()
    client = TestClient(app)

    listing = client.get('/billing/cases?status=OPEN&min_days=20')
    summary = client.get('/billing/cases/summary?status=OPEN&min_days=20')

    assert listing.status_code == 200
    assert summary.status_code == 200

    listed_items = listing.json()
    summary_payload = summary.json()

    assert summary_payload['total_cases'] == len(listed_items)
    assert summary_payload['total_amount_open'] == '280.50'
    assert summary_payload['oldest_due_date'] == '2023-12-15'
    assert summary_payload['by_filial'] == {'A': 1, 'B': 1}


class _SyncTestAdapter:
    def list_contas_receber_atrasadas(self, min_days: int = 20, due_from=None, due_to=None, filial_id=None):
        today = date.today()
        return [
            {
                'id': 'SYNC-30D',
                'id_cliente': 'CLI-30',
                'filial_id': 'X',
                'data_vencimento': (today - timedelta(days=30)).strftime('%Y-%m-%d'),
                'valor_aberto': '120.50',
                'tipo_recebimento': 'PIX',
                'id_contrato': '0',
            },
            {
                'id': 'SYNC-10D',
                'id_cliente': 'CLI-10',
                'filial_id': 'Y',
                'data_vencimento': (today - timedelta(days=10)).strftime('%Y-%m-%d'),
                'valor_aberto': '44.90',
                'tipo_recebimento': 'BOLETO',
            },
            {
                'id': 'SYNC-ZERO',
                'id_cliente': 'CLI-0',
                'filial_id': 'Y',
                'data_vencimento': (today - timedelta(days=35)).strftime('%Y-%m-%d'),
                'valor_aberto': '0',
                'tipo_recebimento': 'BOLETO',
            },
            {
                'id': 'SYNC-BAD-DATE',
                'id_cliente': 'CLI-BAD',
                'filial_id': 'Y',
                'data_vencimento': '0000-00-00',
                'valor_aberto': '10.00',
                'tipo_recebimento': 'BOLETO',
            },
        ]


def test_post_billing_sync_upserts_only_relevant_cases():
    _seed_cases()
    client = TestClient(app)

    app.dependency_overrides[get_ixc_adapter] = lambda: _SyncTestAdapter()
    try:
        response = client.post('/billing/sync?min_days=20')
    finally:
        app.dependency_overrides.pop(get_ixc_adapter, None)

    assert response.status_code == 200
    payload = response.json()
    assert payload['synced'] == 4
    assert payload['upserted'] == 1

    listed = client.get('/billing/cases?status=OPEN').json()
    by_external = {item['external_id']: item for item in listed}
    assert 'SYNC-30D' in by_external
    assert by_external['SYNC-30D']['open_days'] == 30
    assert 'SYNC-BAD-DATE' not in by_external
    assert 'SYNC-10D' not in by_external
    assert 'SYNC-ZERO' not in by_external
