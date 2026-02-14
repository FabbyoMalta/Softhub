from app.adapters.ixc_adapter import MockIXCAdapter
from app.services.billing import build_billing_open_response


def test_billing_open_summary_and_contract_enrich():
    data = build_billing_open_response(MockIXCAdapter())
    assert data['summary']['total_open'] == 2
    assert data['summary']['over_20_days'] >= 1
    assert data['items'][0]['contract']['id'] == '2'
