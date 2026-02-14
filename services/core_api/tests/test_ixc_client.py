from app.clients.ixc_client import IXCClient, IXCClientError


class DummyResponse:
    status_code = 200

    def raise_for_status(self):
        return None

    def json(self):
        return {'type': 'error', 'message': 'falha logica'}


class DummyHttpClient:
    def post(self, *args, **kwargs):
        return DummyResponse()

    def close(self):
        return None


def test_ixc_client_raises_on_type_error_json():
    client = IXCClient(host='host', user='user', token='token', max_retries=1)
    client._client = DummyHttpClient()  # injetado para teste unitário mínimo

    try:
        client.post_list('/cliente_contrato', [], page=1, rp=10, sortname='id', sortorder='asc')
        assert False, 'expected IXCClientError'
    except IXCClientError as exc:
        assert 'falha logica' in str(exc)
