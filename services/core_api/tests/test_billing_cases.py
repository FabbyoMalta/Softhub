from datetime import date, datetime
from decimal import Decimal

from fastapi.testclient import TestClient

from app.db import BillingCase, SessionLocal
from app.main import app


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
